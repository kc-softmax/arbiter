import asyncio
import json
import traceback
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
    ChatEvent, ChatSocketBaseMessage, ChatSocketUserInviteMessage, ChatSocketUserLikeMessage, ClientChatData,
    ChatSocketChatMessage, ClientChatMessage, MessageLikeData, RoomChangeData,
    UserData, ChatSocketErrorMessage, ErrorData,
    ChatSocketNoticeMessage, ChatSocketRoomCreateMessage, UserInviteData
)
from server.database import make_async_session


router = APIRouter(prefix="/chat")

templates = Jinja2Templates(directory="server/chat/templates")

chat_room_manager = ChatRoomManager()
asyncio.create_task(chat_room_manager.lobby_refresh_timer(delay_time=20.0))


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
    await chat_room_manager.join_room(websocket, "DEFAULT", user_data)

    # 소켓 메시지 처리

    while True:
        try:
            data = await websocket.receive_text()
            await asyncio.sleep(0.01)
            json_data = ChatSocketBaseMessage.parse_obj(json.loads(data))

            # join, exit로 나누는게 좋을 꺼 같다.
            if json_data.action == ChatEvent.ROOM_CHANGE:
                # 어떤 방인 지 알 수 없다.
                room_id_from = json_data.data['room_id_from']
                room_id_to = json_data.data['room_id_to']

                # 요청한 방이 없을 경우
                if not room_id_to in chat_room_manager.rooms:
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
                if not chat_room_manager.rooms[room_id_to].is_available():
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
                if chat_room_manager.rooms[room_id_to].is_duplicate(user_data.user_id):
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
                await chat_room_manager.leave_room(websocket, room_id_from, user_data)
                await chat_room_manager.join_room(websocket, room_id_to, user_data)

            if json_data.action == ChatEvent.ROOM_JOIN:
                room_id = json_data.data['room_id']
                # 요청한 방이 없을 경우
                if not room_id in chat_room_manager.rooms:
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
                if not chat_room_manager.rooms[room_id].is_available():
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
                if chat_room_manager.rooms[room_id].is_duplicate(user_data.user_id):
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
                await chat_room_manager.join_room(websocket, room_id, user_data)

            if json_data.action == ChatEvent.MESSAGE:
                receive_room_id = json_data.data['room_id']
                chat_message = await chat_room_manager.rooms[receive_room_id].handle_chat_message(
                    user_data,
                    ClientChatMessage.parse_obj(json_data)
                )
                # 유저들에게 브로드캐스팅
                await connection_manager.send_room_broadcast(
                    receive_room_id,
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
                            # TODO: 수정필요, room_id 의미 없음
                            room_id=room_id,
                            message=f'{room_id} 방이 생성되었습니다.'
                        )
                    )
                )

            if json_data.action == ChatEvent.NOTICE:
                room_id = json_data.data['room_id']
                chat_room_manager.rooms[room_id].notice = json_data.data['message']
                await connection_manager.send_room_broadcast(
                    room_id,
                    ChatSocketNoticeMessage(
                        data=ClientChatData(
                            room_id=room_id,
                            message=json_data.data['message']
                        )
                    )
                )

            if json_data.action == ChatEvent.LOBBY_REFRESH:
                await chat_room_manager.send_lobby_data()

            if json_data.action == ChatEvent.USER_INVITE:
                room_id = json_data.data['room_id']
                user_id_from = json_data.data['user_id_from']
                # user_name not unique
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
                room_id = json_data.data['room_id']
                message_id = json_data.data['message_id']
                type = json_data.data['type']  # like or dislike

                # 단순하게 계산하기
                # TODO: 우선 클라이언트 라디오 버튼으로 중복 클릭 방지 했는데, 서버에서도 중복 클릭 방지를 해야할듯
                for chat in chat_room_manager.rooms[room_id].message_history:
                    if chat.message_id == message_id:
                        chat_data = chat
                        chat.like = chat.like + 1 if type == 'like' else chat.like - 1
                        break

                await connection_manager.send_room_broadcast(
                    room_id,
                    ChatSocketUserLikeMessage(
                        data=MessageLikeData(
                            room_id=room_id,
                            message_id=chat_data.message_id,
                            like=chat_data.like
                        )
                    )
                )
        # 디버깅 용
        except WebSocketDisconnect as e:
            print('1. WebSocket Disconnect exception', e)
            await chat_room_manager.leave_room(websocket, "", user_data)
            break
        except Exception as e:
            print('2. WebSocket Receive exception', e)
            traceback.print_exc()
            continue
