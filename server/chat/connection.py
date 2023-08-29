from fastapi import WebSocket
from collections import defaultdict
from pydantic import BaseModel

from server.auth.utils import verify_token
from server.chat.schemas import ChatSocketBaseMessage, ErrorData


class ConnectionManager:

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, room_id: str, token: str) -> tuple[str, str]:
        # 유효하지 않은 토큰일지라도 그 에러를 응답으로 보내주기 위해서는 먼저 accept을 해줘야한다.
        await websocket.accept()
        token_data = verify_token(token)
        self.active_connections[room_id].append(websocket)
        return token_data.sub

    def disconnect(self, room_id: str, websocket: WebSocket):
        self.active_connections[room_id].remove(websocket)

    async def send_personal_message(self, websocket: WebSocket, message: ChatSocketBaseMessage):
        await websocket.send_json(message.dict())

    async def send_room_broadcast(self, room_id: str, message: ChatSocketBaseMessage):
        connections = self.active_connections[room_id]
        for connection in connections:
            await connection.send_json(message.dict())


connection_manager = ConnectionManager()
