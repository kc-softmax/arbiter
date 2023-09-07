import asyncio
import json
import traceback
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.templating import Jinja2Templates

from server.auth.utils import verify_token
from server.auth.models import User
from server.auth.exceptions import InvalidToken, UserAlreadyConnected
from server.chat import room_manager
from server.chat import lobby_manager
from server.chat.connection import connection_manager
from server.chat.exceptions import (
    AlreadyLeftRoom, AuthorizationFailedClose, MessageIsNotExists, RoomDoesNotExist, AlreadyJoinedRoom,
    RoomIsFull, RoomIsExist, AlreadyConnected, UserDisconnected
)
from server.chat.schemas import (
    ChatData, ChatEvent, ChatSocketBaseMessage, ChatSocketInviteeListMessage, ChatSocketNoticeMessage, ChatSocketUserInviteMessage, ChatSocketUserLeaveMessage,
    ChatSocketUserLikeMessage, ClientChatData, ChatSocketChatMessage, InviteeData,
    MessageLikeData, UserData,
    ChatSocketErrorMessage, ErrorData, ChatSocketRoomCreateMessage, UserInviteData, UserLeaveData
)
from server.chat.schemas import ChatSocketRoomJoinMessage, ChatSocketUserJoinMessage, RoomJoinData, UserJoinData
from server.database import make_async_session


router = APIRouter(prefix="/chat")

templates = Jinja2Templates(directory="server/chat/templates")

asyncio.create_task(lobby_manager.lobby_refresh_timer(delay_time=10.0))


@router.get("/")
async def chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.websocket("/ws")
async def chatroom_ws(websocket: WebSocket, token: str = Query()):

    # 테스트용
    user_id = None
    try:
        if token in ['100', '200', '300', '400', '500']:
            if await room_manager.get_chat_room("lobby") is None:
                await room_manager.create_room("lobby", 100)
                await room_manager.create_room("lobby_0", 100)
                await room_manager.create_room("lobby_1", 100)
                await room_manager.create_room("lobby_2", 100)
                await room_manager.create_room("lobby_3", 100)
                await room_manager.create_room("lobby_4", 100)
                await room_manager.create_room("lobby_5", 100)

            await room_manager.join_room("lobby", int(token))

            await websocket.accept()

            user_id = int(token)
            if user_id in connection_manager.active_connections:
                raise UserAlreadyConnected

            user_data = UserData(
                user_id=user_id,
                user_name=f'test_{user_id}'
            )

            connection_manager.active_connections[user_id] = websocket
        else:
            await websocket.accept()
            token_data = verify_token(token)
            user_id = int(token_data.sub)

            # accept을 해야 token을 검사할 수 있다.
            if user_id in connection_manager.active_connections:
                raise UserAlreadyConnected

            async with make_async_session() as session:
                user = await session.get(User, user_id)

            user_data = UserData(
                user_id=user_id,
                user_name=user.user_name
            )

            connection_manager.active_connections[user_id] = websocket

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

    # 소켓 메시지 처리
    while True:
        try:
            data = await websocket.receive_text()
            await asyncio.sleep(0.01)
            json_data = ChatSocketBaseMessage.parse_obj(json.loads(data))
            print(json_data)

            if json_data.action == ChatEvent.ROOM_CREATE:
                room_id = json_data.data['room_id']
                max_users = json_data.data['max_users']

                if await room_manager.get_chat_room(room_id):
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

                await room_manager.create_room(room_id, max_users)

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

            if json_data.action == ChatEvent.ROOM_JOIN:
                room_id = json_data.data['room_id']
                # 요청한 방이 없을 경우

                chat_room = await room_manager.get_chat_room(room_id)
                if not chat_room:
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
                if await room_manager.is_full(room_id):
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
                if await room_manager.is_joined(room_id, user_id):
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

                if await room_manager.join_room(room_id, user_id):
                    # TODO: 메세지에 담는 항목 Refactoring 필요
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketRoomJoinMessage(
                            data=RoomJoinData(
                                room_id=room_id,
                                messages=room_manager.get_room_messages_nosql(room_id),
                                users=await room_manager.get_room_connected_user_list(room_id),
                                current_users=len(await room_manager.get_room_connected_users(room_id)),
                                max_users=chat_room.max_users,
                                notice=chat_room.notice
                            )
                        )
                    )
                    # 기존에 있었던 유저들에게 새 유저 입장을 알려준다.
                    await connection_manager.send_room_broadcast(
                        room_id,
                        ChatSocketUserJoinMessage(
                            data=UserJoinData(
                                room_id=room_id,
                                user=user_data
                            )
                        )
                    )
            if json_data.action == ChatEvent.ROOM_LEAVE:
                room_id = json_data.data['room_id']
                # 요청한 방이 없을 경우
                if not await room_manager.get_chat_room(room_id):
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

                # 이미 나간 경우
                if not await room_manager.is_joined(room_id, user_id):
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=AlreadyLeftRoom.CODE,
                                reason=AlreadyLeftRoom.REASON
                            )
                        )
                    )
                    continue

                if await room_manager.leave_room(room_id, user_id):
                    await connection_manager.send_room_broadcast(
                        room_id,
                        ChatSocketUserLeaveMessage(
                            data=UserLeaveData(
                                room_id=room_id,
                                user=user_data
                            )
                        )
                    )
            if json_data.action == ChatEvent.NOTICE:
                room_id = json_data.data['room_id']
                notice = json_data.data['message']

                if not await room_manager.get_chat_room(room_id):
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

                if not await room_manager.is_joined(room_id, user_id):
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=AlreadyLeftRoom.CODE,
                                reason=AlreadyLeftRoom.REASON
                            )
                        )
                    )
                    continue

                if await room_manager.set_room_notice(room_id, notice):
                    await connection_manager.send_room_broadcast(
                        room_id,
                        ChatSocketNoticeMessage(
                            data=ClientChatData(
                                room_id=room_id,
                                message=notice
                            )
                        )
                    )

            if json_data.action == ChatEvent.USER_INVITE:
                room_id = json_data.data['room_id']
                user_id_from = json_data.data['user_id_from']
                user_id_to = json_data.data['user_id_to']

                if not user_id_to in connection_manager.active_connections:
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=UserDisconnected.CODE,
                                reason=UserDisconnected.REASON
                            )
                        )
                    )
                    continue

                if not await room_manager.get_chat_room(room_id):
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

                if not user_id_to in connection_manager.active_connections:
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=UserDisconnected.CODE,
                                reason=UserDisconnected.REASON
                            )
                        )
                    )
                    continue

                # 초대이력?
                await connection_manager.send_direct_message(
                    user_id_to,
                    ChatSocketUserInviteMessage(
                        data=UserInviteData(
                            room_id=room_id,
                            user_name_from=user_id_from
                        )
                    )
                )

            if json_data.action == ChatEvent.LOBBY_REFRESH:
                keyword_room_id = json_data.data['keyword_room_id']
                await lobby_manager.send_lobby_data(keyword_room_id)

            # 이벤트 유저 name like
            if json_data.action == ChatEvent.INVITEE_LIST:
                keyword_user_name = json_data.data['keyword_user_name']

                await connection_manager.send_personal_message(
                    websocket,
                    ChatSocketInviteeListMessage(
                        data=await room_manager.get_invitee_users(keyword_user_name)
                    )
                )


            if json_data.action == ChatEvent.MESSAGE_LIKE:
                room_id = json_data.data['room_id']
                message_id = json_data.data['message_id']
                type = json_data.data['type']

                room_manager.set_chat_reaction_nosql(message_id, user_id, type)
                # await room_manager.set_chat_reaction(message_id, user_id, type):
                await connection_manager.send_room_broadcast(
                    room_id,
                    ChatSocketUserLikeMessage(
                        data=MessageLikeData(
                            room_id=room_id,
                            message_id=message_id,
                            like=len(room_manager.get_chat_reaction_by_message_id_nosql(message_id, type='like'))
                        )
                    )
                )

            if json_data.action == ChatEvent.MESSAGE:
                receive_room_id = json_data.data['room_id']
                message = json_data.data['message']

                room_id = json_data.data['room_id']

                # 메시지가 엄청 많을 텐데 계속 검사해줘야 하나?
                if not await room_manager.get_chat_room(room_id):
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

                # 해당 방에 없을 경우
                if not await room_manager.is_joined(room_id, user_id):
                    await connection_manager.send_personal_message(
                        websocket,
                        ChatSocketErrorMessage(
                            data=ErrorData(
                                code=AlreadyLeftRoom.CODE,
                                reason=AlreadyLeftRoom.REASON
                            )
                        )
                    )
                    continue

                chat = await room_manager.save_message(room_id, user_id, message)
                room_manager.save_message_nosql(room_id, user_id, user_data.user_name, message)

                # message_id? chat_id?
                await connection_manager.send_room_broadcast(
                    receive_room_id,
                    ChatSocketChatMessage(
                        data=ChatData(
                            room_id=receive_room_id,
                            message_id=chat.id,
                            message=message,
                            user=user_data,
                            time=chat.created_at.isoformat()
                        )
                    )
                )
        # 디버깅 용
        except WebSocketDisconnect as e:
            print('1. WebSocket Disconnect exception', e)
            del connection_manager.active_connections[user_id]
            await room_manager.leave_all_rooms(user_id)
            break
        except Exception as e:
            print('2. WebSocket Receive exception', e)
            traceback.print_exc()
            continue

