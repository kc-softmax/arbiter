from asyncio import wait_for
import inspect
from typing import Any, Callable, Coroutine
from contextlib import asynccontextmanager
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from arbiter.api.auth.utils import verify_token
from arbiter.api.auth.exceptions import InvalidToken
from arbiter.api.chat.exceptions import AuthorizationFailedClose
from arbiter.api.chat.room import ChatRoomManager, ChatRoom

WAITING_READY_SECOND = 5


class NotReady(Exception):
    pass


class SocketService():
    def __init__(self, chat_room_manager: ChatRoomManager) -> None:
        self.ready = False
        self.chat_room_manager = chat_room_manager
        self.room: ChatRoom
        self.user_id: str
        # TODO error handler
        self.event_handler: dict[str, Callable[[Any, str, ChatRoom], Coroutine | None]] = defaultdict()

    @asynccontextmanager
    async def connect(self, websocket: WebSocket, token: str):
        await websocket.accept()
        room = None
        # 추가적인 유효성 체크가 가능하다.
        try:
            token_data = verify_token(token)

            self.ready = await wait_for(websocket.receive_text(), WAITING_READY_SECOND)
            if not self.ready:
                raise NotReady()

            room = self.chat_room_manager.find_available_room()
            if room is None:
                room = self.chat_room_manager.create_room()
            await room.join(token_data.sub, websocket)

            self.user_id = token_data.sub
            self.room = room

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
                await room.leave(token_data.sub)
                if room.is_empty():
                    await self.chat_room_manager.remove_room(room)
            await self.run_event_handler("exit", None, self.user_id, self.room)

    async def start(self, websocket: WebSocket):
        while True:
            if websocket.client_state != WebSocketState.CONNECTED:
                return
            data = await websocket.receive_json()
            action = data["action"]
            await self.run_event_handler(action, data, self.user_id, self.room)

    def on_event(self, event_type: str):
        def callback_wrapper(callback: Callable):
            self.event_handler[event_type] = callback
            return callback
        return callback_wrapper

    async def run_event_handler(self, event_type: str, *args):
        handler = self.event_handler.get(event_type)
        match event_type:
            case added_event if added_event in self.event_handler.keys():
                if handler:
                    if inspect.iscoroutinefunction(handler):
                        await handler(*args)
                    else:
                        handler(*args)
