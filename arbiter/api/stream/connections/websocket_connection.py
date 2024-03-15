from fastapi.websockets import WebSocketState
from .abstract_connection import ArbiterConnection


class ArbiterWebsocket(ArbiterConnection):

    async def run(self):
        async for message in self.websocket.iter_bytes():
            yield message

    async def send_message(self, bytes: bytes):
        if (self.websocket.client_state is WebSocketState.CONNECTED):
            await self.websocket.send_bytes(bytes)

    async def close(self):
        if (self.websocket.client_state is WebSocketState.CONNECTED):
            await self.websocket.close()

    async def error(self, reason: str | None):
        if (self.websocket.client_state is WebSocketState.CONNECTED):
            await self.websocket.close(reason=reason)
