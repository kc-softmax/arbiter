from fastapi import APIRouter, Request, WebSocket, Query, Depends
from fastapi.templating import Jinja2Templates
from typing import Any

from arbiter.api.auth.dependencies import get_current_user
from arbiter.api.live.legacy.adapter import ChatAdapter
from arbiter.api.live.chat.room import ChatRoom
from arbiter.api.live.legacy.socket import SocketService
from arbiter.api.live.legacy.room import LiveRoomConfig, RoomManager
from arbiter.api.live.chat.schemas import (
    ChatSocketChatMessage,
    ChatSocketRoomJoinMessage,
    ChatSocketUserJoinMessage,
    ChatSocketUserLeaveMessage,
    ClientChatData,
    RoomJoinData,
    UserJoinData,
    UserLeaveData,
)


# Example, 만약에 api 안에서 사용한다면
# @router.post("/match")
# async def request_match(user: User = Depends(get_current_user)):
#     ticket = await match_maker.find_match(user_id=user.id, game_type=MatchType.SOLO)
#     if ticket == None:
#         raise BadRequest
#     if ticket.room_id == None:
#         raise NotFound
#     return {
#         "room_id": ticket.room_id
#     }

router = APIRouter(prefix="/chat")
templates = Jinja2Templates(directory="arbiter/api/live/chat/templates")

chat_room_config = LiveRoomConfig(
    10,
    ChatAdapter,
    "arbiter/api/live/chat/models"
)
chat_room_manager = RoomManager(ChatRoom, chat_room_config)
chat_socket_service = SocketService(chat_room_manager)


@router.get("/")
async def chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket, token: str = Query()):

    @chat_socket_service.on_connection_event("ready")
    def on_ready(self: SocketService, user_id: str):
        print("!!!!!!!!! ready !!!!!!!!!!")

    @chat_socket_service.on_connection_event("create_room")
    def on_create_room(self: SocketService, room: ChatRoom):
        print("!!!!!!!!! on create room !!!!!!!!!!")

    @chat_socket_service.on_connection_event("join_room")
    async def on_join_room(self: SocketService, user_id: str, room: ChatRoom):
        await self.send_personal_message(
            room.room_id,
            user_id,
            ChatSocketRoomJoinMessage(
                data=RoomJoinData(
                    room_id=room.room_id,
                    messages=room.message_history,
                    users=list(room.current_users)
                )
            ).dict()
        )
        await self.room_connections[room.room_id].put_broadcast_message(
            ChatSocketUserJoinMessage(
                data=UserJoinData(
                    user=user_id
                )
            ).dict()
        )

    @chat_socket_service.on_connection_event("leave_room")
    async def on_leave_room(self: SocketService, user_id: str, room: ChatRoom):
        await self.room_connections[room.room_id].put_broadcast_message(
            ChatSocketUserLeaveMessage(
                data=UserLeaveData(
                    user=user_id
                )
            ).dict()
        )

    @chat_socket_service.on_connection_event("destroy_room")
    async def on_destroy_room(self: SocketService, user_id: str, room: ChatRoom):
        print("!!!!!!!!!!! 방 없어짐 !!!!!!!!!!!!!")

    @chat_socket_service.on_connection_event("timeout")
    def on_timout(self: SocketService, user_id: str, room: ChatRoom):
        print("!!!!!!!!!!!!!! 타임 아웃 !!!!!!!!!!!!!!!")

    @chat_socket_service.on_message_event("message")
    async def on_receive_message(self: SocketService, data: Any, user_id: str, room: ChatRoom):
        chat_socket_message = await room.handle_chat_message(
            user_id,
            ClientChatData.parse_obj(data)
        )

        await self.room_connections[room.room_id].put_broadcast_message(
            ChatSocketChatMessage(
                data=chat_socket_message
            ).dict()
        )

    async with chat_socket_service.connect(websocket, token) as result:
        if not result:
            return
        user_id, room = result
        await chat_socket_service.start(websocket, user_id, room, None)
