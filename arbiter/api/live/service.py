from __future__ import annotations
import inspect
import asyncio
from asyncio.tasks import Task
from typing import Any, Callable, Coroutine, Tuple
from contextlib import asynccontextmanager
from collections import defaultdict
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from arbiter.api.live.const import LiveConnectionEvent, LiveConnectionState, LiveSystemEvent
from arbiter.api.live.data import LiveConnection, LiveMessage
from arbiter.api.live.engine import LiveEngine


class LiveService:

    def __init__(self, engine: LiveEngine):
        self.engine: LiveEngine = engine
        self.connections: dict[str, LiveConnection] = defaultdict(
            LiveConnection)
        self.group_connections: dict[str, list[LiveConnection]] = defaultdict(
            list[LiveConnection])
        # 소켓 연결, 방 입장/퇴장 등과 관련된 이벤트 핸들러들
        self.connection_evnet_handlers: dict[str, Callable[[
            Any, str], Coroutine | None]] = defaultdict()
        self.subscribe_to_engine_task: Task = asyncio.create_task(
            self.subscribe_to_engine())

    @asynccontextmanager
    async def connect(self, websocket: WebSocket, user_id: str, team: int, use_adapter: bool) -> Tuple[str, str]:
        await websocket.accept()
        try:
            # TODO: 예제에서 토큰이 매번 필요해서 임시 주석 처리
            # token_data = verify_token(token)
            # user_id = token_data.sub
            # user_id = str(uuid.uuid4())
            user_name = "MG JU HONG"
            setattr(websocket, "user_id", user_id)
            self.connections[user_id] = LiveConnection(websocket)
            await self.run_event_handler(LiveConnectionEvent.VALIDATE)
            self.engine.env.add_agent(user_id, team)
            yield user_id, user_name
            # await subscribe_to_engine
        except Exception as e:
            print(e)
            yield None, None
        finally:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
            # 끝날 때 공통으로 해야할 것
            # 하나의 로직으로 출발해서 순차적으로 종료시켜라
            self.connections.pop(user_id, None)
            await self.engine.remove_user(user_id, use_adapter)
            self.engine.env.remove_agent(user_id)
            print('close, remove user')
            

    async def run_event_handler(self, event_type: LiveConnectionEvent, *args):
        event_handlers = self.connection_evnet_handlers
        handler = event_handlers.get(event_type)
        match event_type:
            case added_event if added_event in event_handlers.keys():
                if handler:
                    if inspect.iscoroutinefunction(handler):
                        await handler(self, *args)
                    else:
                        handler(self, *args)

    # decorators
    def on_connection_event(self, event_type: LiveConnectionEvent):
        def callback_wrapper(callback: Callable):
            self.connection_evnet_handlers[event_type] = callback
            return callback
        return callback_wrapper

    def handle_system_message(self, message: LiveMessage):
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
            case LiveSystemEvent.ERROR:
                # TODO: error handling
                # if target is None ->  send all users
                pass

    async def publish_to_engine(self, websocket: WebSocket, user_id: str, use_adapter: bool = False):
        # send engine to join 
        await self.engine.setup_user(user_id, use_adapter)
        async for message in websocket.iter_bytes():
            # block
            match self.connections[user_id].state:
                case LiveConnectionState.CLOSE:
                    break
                case LiveConnectionState.BLOCK:
                    continue
            live_message = LiveMessage(src=user_id, data=message)
            await self.engine.on(live_message)

    async def subscribe_to_engine(self):
        async with self.engine.subscribe() as engine:
            try:
                async for event in engine:
                    if event.target is None: # send to all
                        await self.send_messages(self.connections.values(), event)
                    elif event.systemEvent:
                        self.handle_system_message(event)
                    elif user_connection := self.connections.get(event.target, None):
                        await self.send_personal_message(user_connection, event)
                    elif group_connections := self.group_connections.get(event.target, None):
                        await self.send_messages(group_connections, event)
                    else:  # send to all
                        raise Exception('not implemented')
            except Exception as e:
                print(e, 'in subscribe_to_engine')

    async def send_personal_message(self, connection: LiveConnection, message: LiveMessage):
        # personal message는 state에 덜 종속적이다. 현재는 pending 상태에서 보낼 수 있다.
        if connection.state == LiveConnectionState.CLOSE:
            return
        await connection.websocket.send_bytes(message.data)

    async def send_messages(self, connections: list[LiveConnection], message: LiveMessage):
        try:
            for connection in connections:
                if connection.state == LiveConnectionState.ACTIVATE:
                    await connection.websocket.send_bytes(message.data)
        except Exception as err:
            print('skip player')


# live_service = LiveService(LiveEngine())


# async def ws(websocket: WebSocket, token: str):
#     async with live_service.connect(websocket, token) as user_id:
#         await live_service.publish_to_engine(websocket, user_id)

    #
