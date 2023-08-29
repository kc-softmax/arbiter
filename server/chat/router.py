import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.templating import Jinja2Templates

from server.auth.exceptions import InvalidToken
from server.auth.utils import verify_token
from server.auth.models import User
from server.chat.connection import connection_manager
from server.chat.room import ChatRoomManager, ChatRoom
from server.chat.exceptions import (
    AuthorizationFailedClose, RoomDoesNotExist, AlreadyJoinedRoom,
    RoomIsFull
)
from server.chat.schemas import (
    ChatEvent, ChatSocketBaseMessage, ClientChatData,
    ChatSocketChatMessage, ClientChatMessage,
    UserData, ChatSocketErrorMessage, ErrorData,
    ChatSocketNoticeMessage
)
from server.database import make_async_session


router = APIRouter(prefix="/chat")

templates = Jinja2Templates(directory="server/chat/templates")

chat_room_manager = ChatRoomManager()


@router.get("/")
async def chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.websocket("/ws")
async def chatroom_ws(websocket: WebSocket, token: str = Query()):
    # TODO 매칭 메이킹이 만들어지면 room id는 query로 받도록 한다.
    # 굳이 방이 없어도 된다.
    temp_room = chat_room_manager.get_by_room_id('DEFAULT')
    if not temp_room:
        chat_room_manager.create_room('DEFAULT')
        chat_room_manager.rooms['DEFAULT'].max_num = 100
        # 방 이동 테스트용 추가
        chat_room_manager.create_room('TEST')
        chat_room_manager.rooms['TEST'].max_num = 100

    user_id = None
    try:
        await websocket.accept()
        token_data = verify_token(token)
        # TODO: 중복접속 방지
        user_id = int(token_data.sub)

        async with make_async_session() as session:
            user = await session.get(User, user_id)

        user_data = UserData(
            user_id=user.id,
            user_name=user.user_name
        )
    except InvalidToken:
        await websocket.close(
            AuthorizationFailedClose.CODE,
            AuthorizationFailedClose.REASON
        )
        return

    # DEFAULT 방에 입장
    await chat_room_manager.join_room(websocket, 'DEFAULT', user_data)

    # 소켓 메시지 처리
    try:
        while True:
            data = await websocket.receive_text()
            json_data = ChatSocketBaseMessage.parse_obj(json.loads(data))

            # 접속한 방 가져오기
            room = chat_room_manager.get_joined_room(user_id)

            if json_data.action == ChatEvent.ROOM_CHANGE:
                receive_room_id = json_data.data['room_id']

                # 요청한 방이 없을 경우
                if not receive_room_id in chat_room_manager.rooms:
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=RoomDoesNotExist.CODE,
                                reason=RoomDoesNotExist.REASON
                            )
                        )
                    )
                    continue

                # full 방인 경우
                if not chat_room_manager.rooms[receive_room_id].is_available():
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=RoomIsFull.CODE,
                                reason=RoomIsFull.REASON
                            )
                        )
                    )
                    continue

                # 같은 방 다시 접속 한 경우
                if chat_room_manager.rooms[receive_room_id].is_duplicate(user_data.user_id):
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=AlreadyJoinedRoom.CODE,
                                reason=AlreadyJoinedRoom.REASON
                            )
                        )
                    )
                    continue
                await chat_room_manager.join_room(websocket, receive_room_id, user_data)

            if json_data.action == ChatEvent.MESSAGE:
                chat_message = await room.handle_chat_message(
                    user_data,
                    ClientChatMessage.parse_obj(json_data)
                )
                # 유저들에게 브로드캐스팅
                await connection_manager.send_room_broadcast(
                    room.room_id,
                    ChatSocketChatMessage(
                        data=chat_message
                    )
                )

            if json_data.action == ChatEvent.NOTICE:
                room.notice = json_data.data['message']
                await connection_manager.send_room_broadcast(
                    room.room_id,
                    ChatSocketNoticeMessage(
                        data=ClientChatData(
                            message=json_data.data['message']
                        )
                    )
                )

    # 연결이 끊김 -> 유저가 채팅을 나갔다.
    except WebSocketDisconnect:
        await chat_room_manager.leave_room(websocket, user_data)
