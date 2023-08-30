import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.templating import Jinja2Templates

from arbiter.api.auth.exceptions import InvalidToken
from arbiter.api.chat.connection import ConnectionManager
from arbiter.api.chat.room import ChatRoomManager
from arbiter.api.chat.exceptions import AuthorizationFailedClose
from arbiter.api.chat.schemas import (
    ChatSocketRoomJoinMessage, RoomJoinData,
    ChatSocketUserJoinMessage, UserJoinData, ChatSocketChatMessage,
    ChatSocketUserLeaveMessage, UserLeaveData, ClientChatMessage
)

router = APIRouter(prefix="/chat")

templates = Jinja2Templates(directory="server/chat/templates")

chat_room_manager = ChatRoomManager()
connection_manager = ConnectionManager()


@router.get("/")
async def chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.websocket("/ws")
async def chatroom_ws(websocket: WebSocket, token: str = Query()):
    # TODO 매칭 메이킹이 만들어지면 room id는 query로 받도록 한다.
    room = chat_room_manager.find_available_room()
    if room is None:
        room = chat_room_manager.create_room()

    # 소켓 연결 및 토큰을 검증하여 user_id를 얻는다.
    try:
        user_id = await connection_manager.connect(websocket, room.room_id, token)
    except InvalidToken:
        await websocket.close(
            AuthorizationFailedClose.CODE,
            AuthorizationFailedClose.REASON
        )
        return
    # 방 입장
    room.join(user_id)
    # 새로 입장한 유저에게 기존 채팅방 데이터를 보내준다.
    await connection_manager.send_personal_message(
        websocket,
        ChatSocketRoomJoinMessage(
            data=RoomJoinData(
                room_id=room.room_id,
                messages=room.message_history,
                users=room.current_users
            )
        )
    )
    # 기존에 있었던 유저들에게 새 유저 입장을 알려준다.
    await connection_manager.send_room_broadcast(
        room.room_id,
        ChatSocketUserJoinMessage(
            data=UserJoinData(
                user=user_id
            )
        )
    )
    # 소켓 메시지 처리
    try:
        while True:
            # 채팅 클라이언트로부터 채팅 메시지를 받음
            data = await websocket.receive_text()
            # 받은 채팅 메시지를 코어 로직으로 돌림, 브로드캐스팅할 메시지 구조로 구성
            chat_message = await room.handle_chat_message(
                user_id,
                ClientChatMessage.parse_obj(json.loads(data))
            )
            # 유저들에게 브로드캐스팅
            await connection_manager.send_room_broadcast(
                room.room_id,
                ChatSocketChatMessage(
                    data=chat_message
                )
            )
    # 연결이 끊김 -> 유저가 채팅을 나갔다.
    except WebSocketDisconnect:
        connection_manager.disconnect(room.room_id, websocket)
        room.leave(user_id)
        if room.is_empty():
            chat_room_manager.remove_room(room)
        else:
            await connection_manager.send_room_broadcast(
                room.room_id,
                ChatSocketUserLeaveMessage(
                    data=UserLeaveData(
                        user=user_id
                    )
                )
            )
