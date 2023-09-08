from fastapi import APIRouter, Request, WebSocket, Query, Depends
from fastapi.templating import Jinja2Templates
from typing import Any

from arbiter.api.auth.models import User
from arbiter.api.auth.dependencies import get_current_user
from arbiter.api.chat.room import ChatRoomManager, ChatRoom
from arbiter.api.chat.schemas import ChatSocketChatMessage, ClientChatMessage
from arbiter.api.match.match_maker import match_maker, MatchType
from arbiter.api.exceptions import NotFound, BadRequest
from arbiter.api.socket import SocketService
from arbiter.api.chat.schemas import (
    ChatSocketRoomJoinMessage, RoomJoinData,
    ChatSocketUserJoinMessage, UserJoinData,
    ChatSocketUserLeaveMessage, UserLeaveData,
    ClientChatMessage
)


router = APIRouter(prefix="/chat")

templates = Jinja2Templates(directory="arbiter/api/chat/templates")


@router.get("/")
async def chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Example, 만약에 api 안에서 사용한다면
@router.post("/match")
async def request_match(user: User = Depends(get_current_user)):
    ticket = await match_maker.find_match(user_id=user.id, game_type=MatchType.SOLO)
    if ticket == None:
        raise BadRequest
    if ticket.room_id == None:
        raise NotFound
    return {
        "room_id": ticket.room_id
    }

chat_room_manager = ChatRoomManager()
socket_service = SocketService(chat_room_manager)


@router.websocket("/jay/ws")
async def test_ws(websocket: WebSocket, token: str = Query()):

    @socket_service.on_connection_event("ready")
    def on_ready(self: SocketService, data: Any, user_id: str, room: ChatRoom):
        print("!!!!!!!!! ready !!!!!!!!!!")

    @socket_service.on_connection_event("create_room")
    def on_create_room(self: SocketService, room: ChatRoom):
        print("!!!!!!!!! on create room !!!!!!!!!!")

    @socket_service.on_connection_event("join_room")
    async def on_join_room(self: SocketService, data: Any, user_id: str, room: ChatRoom):
        await self.send_personal_message(
            room.room_id,
            user_id,
            ChatSocketRoomJoinMessage(
                data=RoomJoinData(
                    room_id=room.room_id,
                    messages=room.message_history,
                    users=list(room.current_users)
                )
            )
        )
        await self.room_connections[room.room_id].put_broadcast_message(
            ChatSocketUserJoinMessage(
                data=UserJoinData(
                    user=user_id
                )
            )
        )

    @socket_service.on_connection_event("leave_room")
    async def on_leave_room(self: SocketService, data: Any, user_id: str, room: ChatRoom):
        await self.room_connections[room.room_id].put_broadcast_message(
            ChatSocketUserLeaveMessage(
                data=UserLeaveData(
                    user=user_id
                )
            )
        )

    @socket_service.on_connection_event("destroy_room")
    async def on_destroy_room(self: SocketService, data: Any, user_id: str, room: ChatRoom):
        print("!!!!!!!!!!! 방 없어짐 !!!!!!!!!!!!!")

    @socket_service.on_message_event("message")
    async def on_receive_message(self: SocketService, data: Any, user_id: str, room: ChatRoom):
        chat_socket_message = await room.handle_chat_message(
            user_id,
            ClientChatMessage.parse_obj(data)
        )
        await self.room_connections[room.room_id].put_broadcast_message(
            ChatSocketChatMessage(
                data=chat_socket_message
            )
        )

    async with socket_service.connect(websocket, token) as result:
        if not result:
            return
        token_data, room = result
        await socket_service.start(websocket, token_data.sub, room)
