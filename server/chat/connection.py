from fastapi import WebSocket
from collections import defaultdict
from pydantic import BaseModel

from server.auth.utils import verify_token
from server.chat.schemas import ChatSocketBaseMessage


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, list[dict[str, WebSocket]]] = defaultdict(list)

    def disconnect(self, room_id: str, websocket: WebSocket, user_id: int):
        # self.active_connections[room_id].remove(websocket)
        self.active_connections[room_id].remove({user_id: websocket})

    async def send_personal_message(self, websocket: WebSocket, message: ChatSocketBaseMessage):
        await websocket.send_json(message.dict())

    async def send_direct_message(self, user_id: int, message: ChatSocketBaseMessage):
        # TODO: 자료형 변경
        for connection_infos in self.active_connections.values():
            for connection_info in connection_infos:
                if user_id in connection_info:
                    connection = connection_info[user_id]
                    await connection.send_json(message.dict())

    async def send_room_broadcast(self, room_id: str, message: ChatSocketBaseMessage):
        connection_infos = self.active_connections[room_id]
        for connection_info in connection_infos:
            for connection in connection_info.values():
                await connection.send_json(message.dict())

    # connection이 이미 끊겼는데 보낸다.
    async def send_broadcast(self, message: ChatSocketBaseMessage):
        for connection_infos in self.active_connections.values():
            for connection_info in connection_infos:
                for connection in connection_info.values():
                    await connection.send_json(message.dict())


connection_manager = ConnectionManager()
