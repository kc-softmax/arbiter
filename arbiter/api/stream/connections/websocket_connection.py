from .abstract_connection import (
    ArbiterConnection,
    Callable,
    StreamMessage,
    Coroutine,
    WebSocket,
    GameUser
)


class ArbiterWebsocket(ArbiterConnection):

    async def run(self, callback: Callable[[StreamMessage], Coroutine]):
        async for message in self.websocket.iter_bytes():
            callback(StreamMessage(message, self.game_user))

    async def send_message(self, bytes: bytes):
        await self.websocket.send_bytes(bytes)

    async def close(self):
        print("close websocket connection")
        pass
