import asyncio

from fastapi import WebSocket
from collections import defaultdict
from pydantic import BaseModel

from server.auth.utils import verify_token
from server.chat.schemas import ChatSocketBaseMessage
from reference.adapter import ChatAdapter


class ConnectionManager:

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self.adapter: dict[str, ChatAdapter] = {}

    def check_validation(self, room_id: str, token: str, adapter: ChatAdapter) -> str:
        self.adapter[room_id] = adapter
        token_data = verify_token(token)
        return token_data.sub

    async def connect(self, websocket: WebSocket, room_id: str) -> None:
        # 유효하지 않은 토큰일지라도 그 에러를 응답으로 보내주기 위해서는 먼저 accept을 해줘야한다.
        await websocket.accept()
        self.active_connections[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        self.active_connections[room_id].remove(websocket)

    async def create_subscription_task(self, room_id: str):
        if len(self.active_connections[room_id]) == 1:
            asyncio.create_task(self.send_chat_broadcast(room_id))

    async def send_personal_message(self, websocket: WebSocket, message: ChatSocketBaseMessage):
        await websocket.send_json(message.dict())

    async def send_room_broadcast(self, room_id: str, message: ChatSocketBaseMessage):
        connections = self.active_connections[room_id]
        for connection in connections:
            await connection.send_json(message.dict())

    async def send_chat_broadcast(self, room_id: str):
        async with self.adapter[room_id].subscribe() as chatting:
            async for message in chatting:
                connections = self.active_connections[room_id]
                for connection in connections:
                    await connection.send_json(message.dict())
