import inspect
import asyncio
import uuid
from typing import Any, Callable, Coroutine, Generic, Literal, Type
from contextlib import asynccontextmanager
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from arbiter.api.auth.exceptions import InvalidToken
from arbiter.api.auth.utils import verify_token
from arbiter.api.live.chat.schemas import ChatSocketBaseMessage
from arbiter.api.live.legacy.exceptions import AuthorizationFailedClose
from arbiter.api.live.legacy.room import BaseLiveRoom, LiveRoomConfig, RoomManager, RoomType


WAITING_READY_SECOND = 5

ConnectionEventType = Literal[
    "ready",
    "create_room",
    "join_room",
    "leave_room",
    "destroy_room",
    "timeout"
]


class IterQueue(asyncio.Queue):
    async def __aiter__(self):
        while True:
            item = await self.get()
            yield item


class NotReady(Exception):
    pass


class RoomConnection:

    def __init__(self) -> None:
        self._websockets: dict[str, WebSocket] = defaultdict()
        self._queue: IterQueue[dict] = IterQueue()
        self._broadcast_task: asyncio.Task = None

    def create_broadcast_task(self, coro: Coroutine):
        self._broadcast_task = asyncio.create_task(coro)

    def cancel_broadcast_task(self):
        self._broadcast_task.cancel()

    def get_websockets(self) -> list[WebSocket]:
        return self._websockets.values()

    def get_websocket_by_user(self, user_id: str) -> WebSocket:
        return self._websockets[user_id]

    def add_websocket(self, user_id: str, websocket: WebSocket):
        self._websockets[user_id] = websocket

    def remove_websocket(self, user_id: str):
        self._websockets.pop(user_id)

    async def put_broadcast_message(self, message: dict):
        await self._queue.put(message)

    def get_broadcast_queue(self) -> IterQueue[dict]:
        return self._queue


class SocketService():
    def __init__(self, room_manager: RoomManager[RoomType]) -> None:
        self.room_manager = room_manager
        # room id 기준 데이터들
        self.room_connections: dict[str, RoomConnection] = defaultdict()
        # 소켓 연결, 방 입장/퇴장 등과 관련된 이벤트 핸들러들
        self.connection_evnet_handlers: dict[str, Callable[[Any, str, BaseLiveRoom], Coroutine | None]] = defaultdict()
        # 소켓으로 받은 메시지에 정의된 이벤트 핸들러들
        self.message_event_handlers: dict[str, Callable[[Any, str, BaseLiveRoom], Coroutine | None]] = defaultdict()

    @asynccontextmanager
    async def connect(
        self,
        websocket: WebSocket,
        token: str,
    ):
        await websocket.accept()
        room = None
        # 추가적인 유효성 체크가 가능하다.
        try:
            # TODO: 예제에서 토큰이 매번 필요해서 임시 주석 처리
            # token_data = verify_token(token)
            # user_id = token_data.sub

            # TEMP
            user_id = str(uuid.uuid4())

            try:
                ready = await asyncio.wait_for(websocket.receive_text(), WAITING_READY_SECOND)
                await self.run_event_handler("ready", False, user_id)
                if not ready:
                    raise NotReady()
            except TimeoutError:
                raise NotReady()

            room = self.room_manager.find_available_room()
            if room is None:
                room = self.room_manager.create_room(None)
                room_connection = RoomConnection()
                room_connection.create_broadcast_task(self.send_room_broadcast(room.room_id))
                self.room_connections[room.room_id] = room_connection
                await self.run_event_handler("create_room", False, room)

            room.join(user_id)
            self.room_connections[room.room_id].add_websocket(user_id, websocket)
            await self.run_event_handler("join_room", False, user_id, room)

            yield user_id, room
        except InvalidToken:
            print("!!!!!!!!!!! 이상한 토큰 !!!!!!!!!!!!!!!!")
            await websocket.close(
                AuthorizationFailedClose.CODE,
                AuthorizationFailedClose.REASON
            )
            yield
        except TimeoutError:
            await self.run_event_handler("timeout", False, user_id, room)
            await websocket.close()
            if ready:
                return
            yield
        except NotReady:
            print("!!!!!!!!!!! 준비 안함 !!!!!!!!!!!!!!!!")
            await websocket.close()
            yield
        except WebSocketDisconnect:
            print("!!!!!!!!!!! 연결 끊김 !!!!!!!!!!!!!!!!")
            if ready:
                return
            yield
        except RuntimeError as e:
            print("!!!!!!!!!!! 런타임 에러 !!!!!!!!!!!!!!!!", e)
            if websocket.client_state != WebSocketState.DISCONNECTED:
                # print(e)
                await websocket.close()
            return
        finally:
            # 끝날 때 공통으로 해야할 것
            if room:
                room.leave(user_id)
                self.room_connections[room.room_id].remove_websocket(user_id)
                await self.run_event_handler("leave_room", False, user_id, room)
                if room.is_empty():
                    await self.room_manager.remove_room(room)
                    self.room_connections[room.room_id].cancel_broadcast_task()
                    await self.run_event_handler("destroy_room", False, user_id, room)

    async def start(self, websocket: WebSocket, user_id: str, room: RoomType, timeout: int | None = None):
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                return
            received_message = None
            if timeout:
                received_message = await asyncio.wait_for(websocket.receive_json(), timeout)
            else:
                received_message = await websocket.receive_json()
            # socket으로 전달받는 메시지 프로토콜
            # action : 어떤 메시지인지 정의(예: user_join 등) / 해당 action은 핸들러에 등록된 이벤트 이름으로 등록됨
            # data: 그 외 전달 받는 데이터
            action = received_message["action"]
            data = received_message["data"]
            await self.run_event_handler(action, True, data, user_id, room)

    async def run_event_handler(self, event_type: ConnectionEventType | str, is_message_event: bool, *args):
        event_handlers = self.message_event_handlers if is_message_event else self.connection_evnet_handlers
        handler = event_handlers.get(event_type)
        match event_type:
            case added_event if added_event in event_handlers.keys():
                if handler:
                    if inspect.iscoroutinefunction(handler):
                        await handler(self, *args)
                    else:
                        handler(self, *args)

    # decorators
    def on_connection_event(self, event_type: ConnectionEventType):
        def callback_wrapper(callback: Callable):
            self.connection_evnet_handlers[event_type] = callback
            return callback
        return callback_wrapper

    def on_message_event(self, event_type: str):
        def callback_wrapper(callback: Callable):
            self.message_event_handlers[event_type] = callback
            return callback
        return callback_wrapper

    # send socket message functions
    async def send_personal_message(self, room_id: str, user_id: str, message: ChatSocketBaseMessage):
        websocket = self.room_connections[room_id].get_websocket_by_user(user_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(message)

    async def send_room_broadcast(self, room_id: str):
        # room이 없는데 실행되는 경우에 대한 예외처리
        room = self.room_manager.get_room(room_id)
        if room is None:
            raise ValueError("Can't find room")
        room_connection = self.room_connections[room_id]
        async for message in room_connection.get_broadcast_queue():
            for websocket in room_connection.get_websockets():
                if websocket.client_state != WebSocketState.DISCONNECTED:
                    await websocket.send_json(message)
