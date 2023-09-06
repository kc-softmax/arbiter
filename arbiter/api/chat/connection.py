import asyncio
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from collections import defaultdict

from arbiter.api.chat.schemas import ChatSocketBaseMessage


class IterQueue(asyncio.Queue):
    async def __aiter__(self):
        while True:
            item = await self.get()
            yield item


class ConnectionManager:

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = defaultdict()
        self.queue: IterQueue = IterQueue()
        self.task = asyncio.create_task(self.start_broadcast_message())

    def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id)

    async def send_personal_message(self, user_id: str, message: ChatSocketBaseMessage):
        websocket = self.active_connections.get(user_id)
        if not websocket or websocket.client_state == WebSocketState.DISCONNECTED:
            return
        await websocket.send_json(message.dict())

    async def start_broadcast_message(self):
        async for message in self.queue:
            for websocket in self.active_connections.values():
                if websocket.client_state != WebSocketState.DISCONNECTED:
                    await websocket.send_json(message.dict())

    async def stop_broadcast_message(self):
        self.task.cancel()
