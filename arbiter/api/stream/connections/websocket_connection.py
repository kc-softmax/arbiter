from fastapi.websockets import WebSocketState
from .abstract_connection import ArbiterConnection


class ArbiterWebsocket(ArbiterConnection):

    async def run(self):
        async for message in self.websocket.iter_bytes():
            yield message

    async def send_message(self, bytes: bytes):
        await self.websocket.send_bytes(bytes)

    async def close(self):
        if (self.websocket.state is WebSocketState.CONNECTED):
            self.websocket.close()
