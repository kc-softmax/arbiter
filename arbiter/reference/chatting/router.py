from fastapi import Request, Response
from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect

from reference.adapter import ChatAdapter
from reference.service import Room, RoomManager
from reference.chatting.chatting_env import ChattingEnv
from reference.chatting.chat_user import ChatUser

import os
import json


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
    path = os.path.dirname(os.path.abspath(__file__))
    file_name = "/models"
    
    # check available room and create room if not exist
    available_room = room_manager.find_available_room()
    if available_room:
        is_join = available_room.join_room(room_id, user_id, websocket)
        if not is_join:
            await websocket.close()
            return
    else:
        adapter = ChatAdapter(path + file_name)
        available_room = room_manager.create_room(room_id, adapter)
        available_room.join_room(room_id, user_id, websocket)
    
    try:
        while True:
            recv_message = await websocket.receive_text()
            # append recv_message to adapter
            message = json.loads(recv_message)
            await available_room.chat_history(room_id, user_id, message['message'])
    except WebSocketDisconnect as err:
        print(err)
        available_room.leave_room(room_id, user_id)
