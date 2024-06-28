from __future__ import annotations
import pickle
import asyncio
import arbiter.api.auth.exceptions as AuthExceptions
from typing import Awaitable, Callable
from fastapi import WebSocket
from arbiter.api.auth.utils import verify_token
from arbiter.api.auth.schemas import UserSchema
from arbiter.api.stream.common import extra_query_params
from arbiter.api.stream.connections import ArbiterConnection, ArbiterWebsocket
from arbiter.broker import RedisBroker
from arbiter.database import get_db, Prisma


class ArbiterStream:
    def __init__(
        self,
        user: UserSchema,
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

    @ classmethod
    async def create(cls, websocket: WebSocket, token: str, redis_broker: RedisBroker):
        # Perform some async operation
        # NOTE(24.06.13) temp_chat_service.py를 테스트 실행 하기 위한 임시 주석
        # token_data = verify_token(token)
        # user = await get_db().user.find_unique(where={"id": int(token_data.sub)})
        # if user == None:
        #     raise AuthExceptions.NotFoundUser
        # if user.access_token != token:
        #     raise AuthExceptions.InvalidToken
        await websocket.accept()
        connection = ArbiterWebsocket(websocket)
        extra = extra_query_params(websocket.query_params)
        # Initialize the instance
        instance = cls(
            UserSchema(**user.__dict__),
            connection,
            redis_broker,
            extra)
        return instance

    async def process_messages(self):
        await self.consumer.subscribe(str(self.user.hash_tag))
        async for message in self.consumer.listen():
            print('consume', message)
            await self.connection.send_message(message)

    async def send_message(self, service_id: str, message: any):
        await self.producer.send(message)

    async def start(self):
        try:
            consume_task = asyncio.create_task(self.process_messages())
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

    async def on_connection_close(self, callback: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
        self.on_connection_close_handler = callback
        return callback

    async def on_connection_open(self, callback: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
        self.on_connection_open_handler = callback
        return callback

    async def on_message_receive(self, callback: Callable[[bytes], Awaitable[None]]) -> Callable[[bytes], Awaitable[None]]:
        self.on_message_receive_handler = callback
        return callback
