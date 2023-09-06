from server.chat import room_manager
from fastapi.websockets import WebSocketState
from server.chat.models import ChatRoomUser
from database import make_async_session
from fastapi import WebSocket
from sqlmodel import select

from server.auth.utils import verify_token
from server.chat.schemas import ChatSocketBaseMessage


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, WebSocket] = {}

    def disconnect(self, user_id: int):
        del self.active_connections[user_id]

    # send_personal_message vs send_direct_message
    async def send_personal_message(self, websocket: WebSocket, message: ChatSocketBaseMessage):
        await websocket.send_json(message.dict())

    async def send_direct_message(self, user_id: int, message: ChatSocketBaseMessage):
        await self.active_connections[user_id].send_json(message.dict())

    async def send_room_broadcast(self, room_id: str, message: ChatSocketBaseMessage):
        users = await room_manager.get_room_connected_users(room_id)
        for user in users:
            # []에서 get으로 바꾸었는데 확인해보기
            await self.active_connections.get(user.user_id).send_json(message.dict())

    # 예외처리 해야함
    async def send_broadcast(self, message: ChatSocketBaseMessage):
        for connection in self.active_connections.values():
            if connection.client_state == WebSocketState.CONNECTED:
                await connection.send_json(message.dict())


connection_manager = ConnectionManager()
