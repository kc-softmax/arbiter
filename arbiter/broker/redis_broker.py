from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
import uuid
import time
import redis.asyncio as aioredis
from warnings import warn
from redis.asyncio.client import PubSub
from typing import AsyncGenerator
from arbiter.constants import ARIBTER_DEFAULT_RPC_TIMEOUT
from arbiter.constants.data import ArbiterMessage
from arbiter.broker.base import MessageBrokerInterface


class RedisBroker(MessageBrokerInterface):
    def __init__(self):
        super().__init__()
        self.client: aioredis.Redis = None
        self.pubsub_map: dict[str, PubSub] = {}

    async def connect(self, temp: str = None):
        async_redis_connection_pool = aioredis.ConnectionPool(
            host='localhost')
        self.client = aioredis.Redis.from_pool(async_redis_connection_pool)

    async def disconnect(self):
        for pubsub in self.pubsub_map.values():
            await pubsub.close()
        await self.client.close()

    async def send_message(
        self,
        target: str,
        raw_message: str | bytes,
        response_ch: str = str(uuid.uuid4()),
        timeout: int = ARIBTER_DEFAULT_RPC_TIMEOUT
    ) -> bytes | None:
        assert timeout > 0, "Timeout must be greater than 0"
        message = ArbiterMessage(data=raw_message, id=response_ch)
        await self.client.rpush(target, message.encode())
        if response_ch is None:
            return None
        response = await self.client.blpop(message.id, timeout=timeout)
        if response:
            return response[1]
        await self.client.delete(message.id)
        return None

    async def async_send_message(
        self,
        target: str,
        raw_message: str | bytes,
        response_ch: str = str(uuid.uuid4()),
    ) -> bytes | None:
        message = ArbiterMessage(data=raw_message, id=response_ch)
        await self.client.rpush(target, message.encode())

    async def push_message(self, target: str, message: bytes):
        await self.client.rpush(target, message)

    async def delete_message(self, message_id: str):
        await self.client.delete(message_id)

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        if channel in self.pubsub_map:
            warn(f"Already subscribed to {channel}")
            return
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        self.pubsub_map[channel] = pubsub
        async for message in self.pubsub_map[channel].listen():
            if message['type'] == 'message':
                yield message['data']
        pubsub = self.pubsub_map.pop(channel)
        await pubsub.unsubscribe(channel)

    async def broadcast(self, topic: str, message: bytes):
        await self.client.publish(topic, message)

    async def listen(
        self,
        channel: str
    ) -> AsyncGenerator[bytes, None]:
        try:
            while True:
                _, message = await self.client.blpop(channel)
                if message:
                    yield message
        except Exception as e:
            print('listen: ', e)

    async def periodic_listen(
        self,
        channel: str,
        period: float = 1
    ) -> AsyncGenerator[list[bytes], None]:
        while True:
            collected_messages = []
            start_time = time.monotonic()

            while (time.monotonic() - start_time) < period:
                # 현재 시간과 시작 시간의 차이를 계산하여 timeout을 조정
                timeout = period - (time.monotonic() - start_time)
                if timeout <= 0:
                    break
                # 비동기적으로 메시지를 가져옴
                _, message = await self.client.lpop(channel, timeout=timeout)
                if message:
                    # 메시지가 있으면 수집하고 continue로 다시 시도
                    collected_messages.append(message)
                    continue

            if collected_messages:
                yield collected_messages
            else:
                # 주기 동안 메시지가 없더라도 빈 리스트를 반환
                yield []
