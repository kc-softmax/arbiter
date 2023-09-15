from __future__ import annotations
import uuid
import inspect
import asyncio
from asyncio.tasks import Task
from typing import Any, Callable, Coroutine
from contextlib import asynccontextmanager
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from live.const import LiveConnectionEvent, LiveConnectionState, LiveSystemEvent
from live.data import LiveConnection, LiveMessage
from live.engine import LiveEngine


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
        self.engine_task: Task = asyncio.create_task(self.engine.run())

    @asynccontextmanager
    async def connect(self, websocket: WebSocket, token: str):
        await websocket.accept()
        try:
            # TODO: 예제에서 토큰이 매번 필요해서 임시 주석 처리
            # token_data = verify_token(token)
            # user_id = token_data.sub
            user_id = str(uuid.uuid4())
            self.connections[user_id] = LiveConnection(websocket)
            await self.run_event_handler(LiveConnectionEvent.VALIDATE)
            yield user_id
            # await subscribe_to_engine
        except Exception as e:
            yield
        finally:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
            # 내가 나가는 경우
            # 끝날 때 공통으로 해야할 것

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

    async def publish_to_engine(self, websocket: WebSocket, user_id: str):
        # send engine to join 
        self.engine.init_user(user_id)        
        async for message in websocket.iter_bytes():
            if self.connections[user_id].state != LiveConnectionState.CLOSE:
                break
            self.engine.on(user_id, message)

    async def subscribe_to_engine(self):
        async with self.engine.subscribe() as engine:
            async for event in engine:
                event: LiveMessage
                if event.systemEvent:
                    self.handle_system_message(event)
                elif user := self.connections.get(event.target, None):
                    self.send_personal_message(self.connections[user], event)
                elif group := self.group_connections.get(event.target, None):
                    self.send_messages(self.group_connections[group], event)
                else:  # send to all
                    self.send_messages(self.connections.values(), event)

    async def send_personal_message(connection: LiveConnection, message: LiveMessage):
        # personal message는 state에 덜 종속적이다. 현재는 pending 상태에서 보낼 수 있다.
        if connection.state == LiveConnectionState.CLOSE:
            return
        await connection.websocket.send_bytes(message.data)

    async def send_messages(connections: list[LiveConnection], message: LiveMessage):
        for connection in connections:
            if connection.state == LiveConnectionState.ACTIVATE:
                await connection.websocket.send_bytes(message.data)


live_service = LiveService(LiveEngine())


# async def ws(websocket: WebSocket, token: str):
#     async with live_service.connect(websocket, token) as user_id:
#         await live_service.publish_to_engine(websocket, user_id)

    #
