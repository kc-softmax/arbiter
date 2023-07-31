from fastapi import Request, Response
from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect
import asyncio

from server.adapter import ChatAdapter
from reference.service import Room
from reference.chatting.chatting_env import ChattingEnv
from reference.chatting.chat_user import ChatUser


router = APIRouter(prefix="/ws/chat")
room = Room()


@router.post("/register")
async def register_user(user: Request, response: Response):
    # response.set_cookie(key="X-Authorization", value=user.username, httponly=True)
    pass


@router.websocket("/room/{room_id}")
async def chat_engine(websocket: WebSocket, room_id: str):
    await websocket.accept()
    init: dict(str | int, str) = await websocket.receive_json()
    sender: str = init['sender']
    chat_user: ChatUser = ChatUser(sender)
    
    # check available room and create room if not exist
    if room.adapters.get(room_id) and not room.game_state[room_id]:
        is_join = room.join_room(room_id, sender, chat_user, websocket)
        if not is_join:
            await websocket.close()
            return
    else:
        chat_env = ChattingEnv([chat_user])
        adapter = ChatAdapter(chat_env)
        room.attach_adapter(room_id, adapter)
        room.join_room(room_id, sender, chat_user, websocket)
    
    try:
        while True:
            recv_message = await websocket.receive_text()
            # append recv_message to adapter
            await room.chat_history(room_id, sender, recv_message)
    except WebSocketDisconnect as err:
        print(err)
        room.leave_room(room_id)
