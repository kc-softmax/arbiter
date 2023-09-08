import inspect
import asyncio
from typing import Any, Callable, Coroutine
from contextlib import asynccontextmanager
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from arbiter.api.auth.utils import verify_token
from arbiter.api.auth.exceptions import InvalidToken
from arbiter.api.chat.exceptions import AuthorizationFailedClose
from arbiter.api.chat.room import ChatRoomManager, ChatRoom
from arbiter.api.chat.schemas import ChatSocketBaseMessage

WAITING_READY_SECOND = 5


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
        self._queue: IterQueue[ChatSocketBaseMessage] = IterQueue()
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

    async def put_broadcast_message(self, message: ChatSocketBaseMessage):
        await self._queue.put(message)

    def get_broadcast_queue(self) -> IterQueue[ChatSocketBaseMessage]:
        return self._queue


class SocketService():
    def __init__(self, chat_room_manager: ChatRoomManager) -> None:
        self.ready = False
        self.chat_room_manager = chat_room_manager
        # room id 기준 데이터들..
        self.room_connections: dict[str, RoomConnection] = defaultdict()
        # 소켓 연결, 방 입장/퇴장 등과 관련된 이벤트 핸들러들
        self.connection_evnet_handlers: dict[str, Callable[[Any, str, ChatRoom], Coroutine | None]] = defaultdict()
        # 소켓으로 받은 메시지에 정의된 이벤트 핸들러들
        self.message_event_handlers: dict[str, Callable[[Any, str, ChatRoom], Coroutine | None]] = defaultdict()

    @asynccontextmanager
    async def connect(self, websocket: WebSocket, token: str):
        await websocket.accept()
        room = None
        # 추가적인 유효성 체크가 가능하다.
        try:
            token_data = verify_token(token)
            user_id = token_data.sub

            self.ready = await asyncio.wait_for(websocket.receive_text(), WAITING_READY_SECOND)
            if not self.ready:
                raise NotReady()

            room = self.chat_room_manager.find_available_room()
            if room is None:
                room = self.chat_room_manager.create_room()
                room_connection = RoomConnection()
                room_connection.create_broadcast_task(self.send_room_broadcast(room.room_id))
                self.room_connections[room.room_id] = room_connection
                await self.run_event_handler("create_room", False, room)

            room.join(user_id, websocket)
            self.room_connections[room.room_id].add_websocket(user_id, websocket)
            await self.run_event_handler("join_room", False, None, user_id, room)

            yield token_data, room
        except InvalidToken:
            print("!!!!!!!!!!! 이상한 토큰 !!!!!!!!!!!!!!!!")
            await websocket.close(
                AuthorizationFailedClose.CODE,
                AuthorizationFailedClose.REASON
            )
            yield
        except TimeoutError:
            print("!!!!!!!!!!! 타임 아웃 !!!!!!!!!!!!!!!!")
            await websocket.close()
            if self.ready:
                return
            yield
        except NotReady:
            print("!!!!!!!!!!! 준비 안함 !!!!!!!!!!!!!!!!")
            await websocket.close()
            yield
        except WebSocketDisconnect:
            print("!!!!!!!!!!! 연결 끊김 !!!!!!!!!!!!!!!!")
            if self.ready:
                return
            yield
        except RuntimeError as e:
            print("!!!!!!!!!!! 런타임 에러 !!!!!!!!!!!!!!!!", e)
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
            return
        finally:
            # 끝날 때 공통으로 해야할 것
            if room:
                await room.leave(user_id)
                self.room_connections[room.room_id].remove_websocket(user_id)
                await self.run_event_handler("leave_room", False, None, user_id, room)
                if room.is_empty():
                    await self.chat_room_manager.remove_room(room)
                    self.room_connections[room.room_id].cancel_broadcast_task()
                    await self.run_event_handler("destroy_room", False, None, user_id, room)

    async def start(self, websocket: WebSocket, user_id: str, room: ChatRoom, timeout: int | None = None):
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                return
            data = None
            if timeout:
                data = await asyncio.wait_for(websocket.receive_json(), timeout)
            else:
                data = await websocket.receive_json()
            action = data["action"]
            await self.run_event_handler(action, True, data, user_id, room)

    async def run_event_handler(self, event_type: str, is_message_event: bool, *args):
        event_handlers = self.message_event_handlers if is_message_event else self.connection_evnet_handlers
        handler = event_handlers.get(event_type)
        match event_type:
            case added_event if added_event in event_handlers.keys():
                if handler:
                    if inspect.iscoroutinefunction(handler):
                        await handler(self, *args)
                    else:
                        handler(self, *args)

    """
    decorators
    """

    def on_connection_event(self, event_type: str):
        def callback_wrapper(callback: Callable):
            self.connection_evnet_handlers[event_type] = callback
            return callback
        return callback_wrapper

    def on_message_event(self, event_type: str):
        def callback_wrapper(callback: Callable):
            self.message_event_handlers[event_type] = callback
            return callback
        return callback_wrapper

    """
    send socket message functions
    """
    async def send_personal_message(self, room_id: str, user_id: str, message: ChatSocketBaseMessage):
        websocket = self.room_connections[room_id].get_websocket_by_user(user_id)
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(message.dict())

    async def send_room_broadcast(self, room_id: str):
        # room이 없는데 실행되는 경우에 대한 예외처리
        room = self.chat_room_manager.get_room(room_id)
        if room is None:
            raise ValueError("Can't find room")
        room_connection = self.room_connections[room_id]
        async for message in room_connection.get_broadcast_queue():
            for websocket in room_connection.get_websockets():
                if websocket.client_state != WebSocketState.DISCONNECTED:
                    await websocket.send_json(message.dict())
