from __future__ import annotations
import inspect
import asyncio
import uuid

from asyncio.tasks import Task
from typing import Any, Callable, Coroutine, Tuple
from contextlib import asynccontextmanager
from collections import defaultdict
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from arbiter.api.auth.repository import game_uesr_repository
from arbiter.api.match.repository import game_access_repository, game_rooms_repository
from arbiter.api.auth.utils import verify_token
from arbiter.api.live.const import LiveConnectionEvent, LiveConnectionState, LiveSystemEvent
from arbiter.api.live.data import LiveConnection, LiveMessage, LiveAdapter
from arbiter.api.live.engine import AsyncService, LiveRoom
from arbiter.api.auth.dependencies import unit_of_work
from arbiter.api.match.models import UserState, GameAccess, GameRooms


class LiveService:

    def __init__(self):
        self.async_service = AsyncService()
        self.live_rooms: dict[str, LiveRoom] = {}
        self.connections: dict[str, LiveConnection] = {}
        self.group_connections: dict[str,
            list[LiveConnection]] = defaultdict(list)
        # 소켓 연결, 방 입장/퇴장 등과 관련된 이벤트 핸들러들
        self.event_handlers: dict[str, Callable[[
            Any, str], Coroutine | None]] = defaultdict()
        self.subscribe_to_service_task: Task = asyncio.create_task(
            self.subscribe_to_service())

    @asynccontextmanager
    async def connect(self, websocket: WebSocket, token: str, room_id: str) -> Tuple[str, str, str]:
        await websocket.accept()
        try:
            token_data = verify_token(token)
            user_id = token_data.sub
            # 임시 user_id
            # user_id = str(uuid.uuid4())
            async with unit_of_work.transaction() as session:
                user = await game_uesr_repository.get_by_id(session, int(user_id))
                if user == None:
                    raise Exception("유저를 찾을 수 없습니다.")
                if user.access_token != token:
                    raise Exception("유효하지 않은 토큰입니다.")

            self.connections[user_id] = LiveConnection(websocket)
            # room에 들어왔을 때 DB에 추가
            user_access = await self.enter_room(room_id, user_id)

            # divide user and bot group using adapter_name
            if user.adapter:
                self.add_group('default_bot_group', self.connections[user_id])
            else:
                # 모든 유저에게 데이터가 전송된다
                self.add_group('default_user_group', self.connections[user_id])
                # room_id에 속한 유저에게 데이터가 전송된다
                self.add_group(room_id, self.connections[user_id])

            await self.run_event_handler(LiveConnectionEvent.VALIDATE, user_id)
            yield user_id, user.user_name, user.adapter
        except Exception as e:
            print(e)
            yield None, None, None
        finally:
            # 끝날 때 공통으로 해야할 것
            # 하나의 로직으로 출발해서 순차적으로 종료시켜라
            self.remove_group(self.connections[user_id])
            self.connections.pop(user_id, None)
            # room에서 나갔을 때 DB에서 update
            await self.leave_room(user_access)

    def add_group(self, group_name: str, connection: LiveConnection):
        if group_name in connection.joined_groups:
            return
        self.group_connections[group_name].append(connection)
        connection.joined_groups.append(group_name)

    def remove_group(self, connection: LiveConnection):
        for group_name in connection.joined_groups:
            self.group_connections[group_name].remove(connection)
        connection.joined_groups = []

    async def set_adapter(self, user_id: str, adapter: LiveAdapter):
        self.connections[user_id].adapter = adapter

    async def run_event_handler(self, event_type: LiveConnectionEvent | LiveSystemEvent, *args):
        event_handlers = self.event_handlers
        handler = event_handlers.get(event_type)
        match event_type:
            case added_event if added_event in event_handlers.keys():
                if handler:
                    if inspect.iscoroutinefunction(handler):
                        await handler(*args)
                    else:
                        handler(*args)

    # decorators
    def on_event(self, event_type: LiveConnectionEvent | LiveSystemEvent):
        def callback_wrapper(callback: Callable):
            self.event_handlers[event_type] = callback
            return callback
        return callback_wrapper

    async def create_room(self, max_player: int = 16) -> str:
        async with unit_of_work.transaction() as session:
            record = await game_rooms_repository.add(
                session,
                GameRooms(
                    game_id=uuid.uuid4().hex,
                    max_player=max_player
                )
            )
            room_id = str(record.id)
            return room_id

    def add_room(self, room_id: str, live_room: LiveRoom):
        self.live_rooms[room_id] = live_room

    async def enter_room(self, room_id: str, user_id: str) -> GameAccess:
        async with unit_of_work.transaction() as session:
            record = await game_access_repository.add(
                session,
                GameAccess(
                    user_id=user_id,
                    game_rooms_id=int(room_id)
                )
            )
            return record

    async def leave_room(self, user: GameAccess):
        async with unit_of_work.transaction() as session:
            user.user_state = UserState.LEFT
            await game_access_repository.update(
                session,
                user
            )

    async def handle_system_message(self, message: LiveMessage):
        match LiveSystemEvent(message.systemEvent):
            case LiveSystemEvent.JOIN_GROUP:
                if connection := self.connections.get(message.target, None):
                    self.group_connections[message.data].append(connection)
            case LiveSystemEvent.LEAVE_GROUP:
                if connection := self.connections.get(message.target, None):
                    self.group_connections[message.data].remove(connection)
            case LiveSystemEvent.REMOVE_GROUP:
                if group := self.group_connections.get(message.data, None):
                    del self.group_connections[group]
            case LiveSystemEvent.KICK_USER:
                if connection := self.connections.get(message.target, None):
                    connection.state = LiveConnectionState.CLOSE
                    if connection.websocket.application_state == WebSocketState.CONNECTED:
                        await connection.websocket.close()
                    await self.run_event_handler(LiveSystemEvent.KICK_USER, message.target)
            case LiveSystemEvent.SAVE_USER_RECORD:
                await self.run_event_handler(LiveSystemEvent.SAVE_USER_RECORD, message.target, message.data)
            case LiveSystemEvent.ERROR:
                # TODO: error handling
                # if target is None ->  send all users
                pass

    async def publish_to_room(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str):
        # send room to join
        await self.live_rooms[room_id].setup_user(room_id, user_id, user_name)
        try:
            async for message in websocket.iter_bytes():
                # block
                if user_id not in self.connections:
                    continue  # TODO remove handling
                match self.connections[user_id].state:
                    case LiveConnectionState.CLOSE:
                        break
                    case LiveConnectionState.BLOCK:
                        continue
                if self.connections[user_id].adapter:
                    adapt_message = await self.connections[user_id].adapter.adapt_in(message)
                    live_message = LiveMessage(src=user_id, data=adapt_message)
                else:
                    live_message = LiveMessage(src=user_id, data=message)
                await self.live_rooms[room_id].on(room_id, live_message)
        except Exception as e:
            print(e, 'in publish_to_room')
            raise e

    async def subscribe_to_service(self):
        async with self.async_service.subscribe() as service:
            try:
                async for event in service:
                    # deprecated 10.10
                    # if event.target is None: # send to all
                    #     await self.send_messages(self.connections.values(), event)
                    if event.systemEvent:
                        await self.handle_system_message(event)
                    elif user_connection := self.connections.get(event.target, None):
                        await self.send_personal_message(user_connection, event)
                    elif group_connections := self.group_connections.get(event.target, None):
                        await self.send_messages(group_connections, event)
                    else:  # send to all
                        continue  # TODO remove handling
                        # raise Exception('not implemented')
            except Exception as e:
                print(e, 'in subscribe_to_service')
                raise e

    async def send_personal_message(self, connection: LiveConnection, message: LiveMessage):
        # personal message는 state에 덜 종속적이다. 현재는 pending 상태에서 보낼 수 있다.
        if connection.state == LiveConnectionState.CLOSE:
            return
        await connection.send_message(message.data)

    async def send_messages(self, connections: list[LiveConnection], message: LiveMessage):
        for connection in connections:
            # 일반적인 메세지는 pending 상태에서 보낼 수 없다.
            if connection.state == LiveConnectionState.ACTIVATE:
                await connection.send_message(message.data)
