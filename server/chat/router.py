import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.templating import Jinja2Templates

from server.auth.exceptions import InvalidToken
from server.auth.utils import verify_token
from server.chat.connection import ConnectionManager
from server.chat.room import ChatRoomManager
from server.chat.exceptions import AuthorizationFailedClose
from server.chat.schemas import (
    ChatEvent, ChatSocketBaseMessage, ChatSocketRoomJoinMessage, RoomJoinData,
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
            data = await websocket.receive_text()
            json_data = ChatSocketBaseMessage.parse_obj(json.loads(data))

            if json_data.action == ChatEvent.ROOM_CHANGE:
                # 접속되어 있는 방 떠나기
                if room:
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
                # 방으로 들어가기
                receive_room_id = json_data.data['room_id']
                room = chat_room_manager.get_by_room_id(receive_room_id)

                # 없을 경우 중단
                if room is None:
                    # raise Exception("존재하지 않는 방입니다.")
                    # 새로운 채널로 가는 개념
                    room = chat_room_manager.create_room(receive_room_id)

                # 이미 accept이 되서 connection_manager 만 연결
                connection_manager.active_connections[receive_room_id].append(websocket)
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

            if json_data.action == ChatEvent.MESSAGE:
                # 받은 채팅 메시지를 코어 로직으로 돌림, 브로드캐스팅할 메시지 구조로 구성
                chat_message = await room.handle_chat_message(
                    user_id,
                    # 위에서 처리 하면 좋을 듯
                    ClientChatMessage.parse_obj(json_data)
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
