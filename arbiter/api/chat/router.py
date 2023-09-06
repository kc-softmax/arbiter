from typing import Any
from fastapi import APIRouter, Request, WebSocket, Query, Depends
from fastapi.templating import Jinja2Templates

from arbiter.api.auth.models import User
from arbiter.api.auth.dependencies import get_current_user
from arbiter.api.chat.room import ChatRoomManager, ChatRoom
from arbiter.api.chat.schemas import ClientChatMessage
from arbiter.api.match.match_maker import match_maker, MatchType
from arbiter.api.exceptions import NotFound, BadRequest
from arbiter.api.socket import SocketService

router = APIRouter(prefix="/chat")

templates = Jinja2Templates(directory="arbiter/api/chat/templates")

chat_room_manager = ChatRoomManager()


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


@router.websocket("/jay/ws")
async def test_ws(websocket: WebSocket, token: str = Query()):
    socket_service = SocketService(chat_room_manager)

    @socket_service.on_event("message")
    async def on_message(data: Any, user_id: str, room: ChatRoom):
        await room.handle_chat_message(
            user_id,
            ClientChatMessage.parse_obj(data)
        )

    @socket_service.on_event("ready")
    def on_ready(data: Any, user_id: str, room: ChatRoom):
        print("!!!!!!!!! ready !!!!!!!!!!")

    @socket_service.on_event("exit")
    def on_exit(data: Any, user_id: str, room: ChatRoom):
        print("!!!!!!! exit !!!!!!!")

    async with socket_service.connect(websocket, token) as result:
        if not result:
            return
        await socket_service.start(websocket)
