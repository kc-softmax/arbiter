from __future__ import annotations
import asyncio
import arbiter.api.auth.exceptions as AuthExceptions
from typing import Awaitable, Callable
from fastapi import WebSocket
from arbiter.api.auth.utils import verify_token
from arbiter.api.stream.common import extra_query_params
from arbiter.api.stream.connections import ArbiterConnection, ArbiterWebsocket
from arbiter.broker.base import MessageConsumerInterface, MessageProducerInterface
from arbiter.broker.redis_broker import RedisBroker
from arbiter.database import get_db, Prisma


class ArbiterStream:
    def __init__(
        self,
        user: Prisma.user,
        connection: ArbiterConnection,
        redis_broker: RedisBroker,
        extra: dict = None,
    ) -> None:
        self.user = user
        self.connection = connection
        self.redis_broker = redis_broker
        self.extra = extra
        self.on_connection_open_handler: Callable[[], Awaitable[None]] = None
        self.on_connection_close_handler: Callable[[], Awaitable[None]] = None
        self.on_message_receive_handler: Callable[[
            bytes], Awaitable[None]] = None

    @property
    def producer(self) -> MessageProducerInterface:
        return self.redis_broker.producer

    @property
    def consumer(self) -> MessageConsumerInterface:
        return self.redis_broker.consumer

    @ classmethod
    async def create(cls, websocket: WebSocket, token: str, redis_broker: RedisBroker):
        # Perform some async operation
        token_data = verify_token(token)
        user = await get_db().user.find_unique(where={"id": int(token_data.sub)})
        if user == None:
            raise AuthExceptions.NotFoundUser
        if user.accessToken != token:
            raise AuthExceptions.InvalidToken
        await websocket.accept()
        connection = ArbiterWebsocket(websocket)
        extra = extra_query_params(websocket.query_params)
        # Initialize the instance
        instance = cls(user, connection, redis_broker, extra)

        return instance

    async def _consume(
        self,
        consumer: MessageConsumerInterface
    ):
        async for message in consumer.listen():
            print('consume', message)
            await self.connection.send_message(message)

    async def start(self):
        # await self.redis_broker.consumer.subscribe(user_id)
        try:
            consume_task = asyncio.create_task(
                self._consume(
                    self.redis_broker.consumer,
                ))
            # 소켓 연결 완료 콜백 실행
            await self.on_connection_open()
            async for message in self.connection.run():
                # 유저 메시지를 받으면 유저 메시지 콜백 실행
                await self.on_message_receive(message)
        except Exception as e:
            print(f"[Stream Error] {e}")
        finally:
            await self.on_connection_close()
            if consume_task is not None:
                consume_task.cancel()
            await self.connection.close()

    async def on_connection_close(self):
        if self.on_connection_close_handler:
            await self.on_connection_close_handler()

    async def on_connection_open(self):
        if self.on_connection_open_handler:
            await self.on_connection_open_handler()

    async def on_message_receive(self, message: bytes):
        if self.on_message_receive_handler:
            await self.on_message_receive_handler(message)
