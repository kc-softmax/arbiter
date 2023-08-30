from fastapi import Request, Response
from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio

from arbiter.api.adapter import ChatAdapter
from reference.service import Room, RoomManager
from reference.chatting.chatting_env import ChattingEnv
from reference.chatting.chat_user import ChatUser


router = APIRouter(prefix="/ws/chat")
room_manager = RoomManager()


@router.post("/register")
async def register_user(user: Request, response: Response):
    # response.set_cookie(key="X-Authorization", value=user.username, httponly=True)
    pass


@router.websocket("/room/{room_id}")
async def chat_engine(websocket: WebSocket, room_id: str):
    await websocket.accept()
    init: dict(str | int, str) = await websocket.receive_json()
    user_id: str = init['sender']
    chat_user: ChatUser = ChatUser(user_id)

    # check available room and create room if not exist
    available_room = room_manager.find_available_room()
    if available_room:
        is_join = available_room.join_room(room_id, user_id, chat_user, websocket)
        if not is_join:
            await websocket.close()
            return
    else:
        chat_env = ChattingEnv([chat_user])
        adapter = ChatAdapter(chat_env)
        available_room = room_manager.create_room(room_id, adapter)
        available_room.join_room(room_id, user_id, chat_user, websocket)

    try:
        while True:
            recv_message = await websocket.receive_text()
            # append recv_message to adapter
            await available_room.chat_history(room_id, user_id, recv_message)
    except WebSocketDisconnect as err:
        print(err)
        available_room.leave_room(user_id)
