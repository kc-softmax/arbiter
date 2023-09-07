
# room_manager에 있는게 맞을까?
import asyncio

from server.chat import room_manager
from server.chat.schemas import ChatSocketLobbyRefreshMessage, LobbyData
from server.chat.connection import connection_manager


async def lobby_refresh_timer(delay_time: float):
    while True:
        await send_lobby_data()
        await asyncio.sleep(delay_time)


async def send_lobby_data(keyword_room_id: str = ''):
    lobby_data = []
    active_rooms = await room_manager.get_chat_active_rooms(keyword_room_id)
    for room in active_rooms:
        lobby_data.append(
            LobbyData(
                room_id=room.room_id,
                current_users=len(await room_manager.get_room_connected_users(room.room_id)),
                max_users=room.max_users
            )
        )

    await connection_manager.send_broadcast(
        ChatSocketLobbyRefreshMessage(
            data=lobby_data
        )
    )


# 현재 접속 중인 유저들 목록
async def send_connected_user_data():
    pass

# 일정 시간 방에 미접속 시 강제 DISCONNECT
async def disconnect_no_action_user():
    pass
