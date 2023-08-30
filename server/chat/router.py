import asyncio
import json
import threading
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.templating import Jinja2Templates

from server.auth.exceptions import InvalidToken, UserAlreadyConnected
from server.auth.utils import verify_token
from server.auth.models import User
from server.chat.connection import connection_manager
from server.chat.room import ChatRoomManager, ChatRoom
from server.chat.exceptions import (
    AuthorizationFailedClose, RoomDoesNotExist, AlreadyJoinedRoom,
    RoomIsFull, RoomIsExist, AlreadyConnected
)
from server.chat.schemas import (
    ChatEvent, ChatSocketBaseMessage, ChatSocketUserInviteMessage, ClientChatData,
    ChatSocketChatMessage, ClientChatMessage, RoomChangeData,
    UserData, ChatSocketErrorMessage, ErrorData,
    ChatSocketNoticeMessage, ChatSocketRoomCreateMessage, UserInviteData
)
from server.database import make_async_session


router = APIRouter(prefix="/chat")

templates = Jinja2Templates(directory="server/chat/templates")

chat_room_manager = ChatRoomManager()
asyncio.create_task(chat_room_manager.lobby_refresh_timer(delay_time=5.0))


@router.get("/")
async def chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.websocket("/ws")
async def chatroom_ws(websocket: WebSocket, token: str = Query()):
    # TODO 매칭 메이킹이 만들어지면 room id는 query로 받도록 한다.
    # 굳이 방이 없어도 된다.
    # TODO: 삭제
    temp_room = chat_room_manager.get_by_room_id('DEFAULT')
    if not temp_room:
        chat_room_manager.create_room('DEFAULT')
        chat_room_manager.rooms['DEFAULT'].max_num = 100
        # 방 이동 테스트용 추가
        for i in range(10):
            chat_room_manager.create_room(f'TEST_{i}')
            chat_room_manager.rooms[f'TEST_{i}'].max_num = 100

    user_id = None
    try:
        await websocket.accept()
        token_data = verify_token(token)
        user_id = int(token_data.sub)

        # 중복 접속 막기
        if user_id in chat_room_manager.user_in_room:
            raise UserAlreadyConnected

        async with make_async_session() as session:
            user = await session.get(User, user_id)

        user_data = UserData(
            user_id=user.id,
            user_name=user.user_name
        )
    except UserAlreadyConnected:
        await websocket.close(
            AlreadyConnected.CODE,
            AlreadyConnected.REASON
        )
        return
    except InvalidToken:
        await websocket.close(
            AuthorizationFailedClose.CODE,
            AuthorizationFailedClose.REASON
        )
        return

    # TODO: 삭제
    # 테스트하기 편하게 DEFAULT 방에 입장하도록 한다
    await chat_room_manager.join_room(websocket, 'DEFAULT', user_data)

    # 소켓 메시지 처리
    try:
        while True:
            data = await websocket.receive_text()
            await asyncio.sleep(0.01)
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

            if json_data.action == ChatEvent.ROOM_CREATE:
                room_id = json_data.data['room_id']
                max_users = json_data.data['max_users']
                # 이미 있는 방인 경우
                if room_id in chat_room_manager.rooms:
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=RoomIsExist.CODE,
                                reason=RoomIsExist.REASON
                            )
                        )
                    )
                    continue

                chat_room_manager.create_room(room_id)
                chat_room_manager.rooms[room_id].max_num = max_users

                await connection_manager.send_personal_message(
                    websocket,
                    ChatSocketRoomCreateMessage(
                        data=ClientChatData(
                            message=f'{room_id} 방이 생성되었습니다.'
                        )
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

            if json_data.action == ChatEvent.LOBBY_REFRESH:
                await chat_room_manager.send_lobby_data()
                # 제어?
                # chat_room_manager.is_timer_on = json_data.data['is_timer_on']
                # chat_room_manager.delay_time = json_data.data['delay_time']

            if json_data.action == ChatEvent.USER_INVITE:
                print(json_data.data)
                room_id = json_data.data['room_id']
                user_id_from = json_data.data['user_id_from']
                user_name_to = json_data.data['user_name_to']
                user_id_to = None
                user_name_from = None

                # 우선 전체 순회를 하자
                # user_name으로 user_id를 찾는다
                for room in chat_room_manager.rooms.values():
                    for user in room.current_users:
                        if user.user_name == user_name_to:
                            user_id_to = user.user_id

                # user_id로 user_name을 찾는다
                for room in chat_room_manager.rooms.values():
                    for user in room.current_users:
                        if user.user_id == user_id_from:
                            user_name_from = user.user_name

                await connection_manager.send_direct_message(
                    user_id_to,
                    ChatSocketUserInviteMessage(
                        data=UserInviteData(
                            room_id=room_id,
                            user_name_from=user_name_from
                        )
                    )
                )

            if json_data.action == ChatEvent.MESSAGE_LIKE:
                message_id = json_data.data['message_id']
                type = json_data.data['type']  # like or dislike
                if type == 'like':
                    await room.message_history[message_id].like_ids.add(user_id)

                await room.message_history[message_id].dislike_ids.add(user_id)

    # 연결이 끊김 -> 유저가 채팅을 나갔다.
    except WebSocketDisconnect:
        await chat_room_manager.leave_room(websocket, user_data)
