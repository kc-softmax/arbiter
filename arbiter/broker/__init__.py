from __future__ import annotations
import time
from abc import ABC, abstractmethod
from typing import AsyncGenerator
import redis.asyncio as aioredis
from arbiter.constants import (
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_SYSTEM_QUEUE,
    ArbiterMessage
)
"""
잠시 구현을 위해 따로 만들어둔다.
다 만든다음 추상화를 해보자
"""


class MessageBrokerInterface(ABC):

    @abstractmethod
    async def subscribe(self, channel: str):
        raise NotImplementedError

    @abstractmethod
    async def unsubscribe(self, channel: str):
        raise NotImplementedError

    @abstractmethod
    async def connect(self):
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self):
        raise NotImplementedError

    @abstractmethod
    async def delete_message(self, message_id: str):
        raise NotImplementedError

    @abstractmethod
    async def publish(self, channel: str, message: bytes):
        raise NotImplementedError

    @abstractmethod
    def listen(self) -> AsyncGenerator[any, None]:
        raise NotImplementedError

    @abstractmethod
    async def send_request_and_wait_for_response(
        self,
        queue: str,
        message: ArbiterMessage,
        timeout: int = 3,
    ) -> ArbiterMessage | None:
        raise NotImplementedError


class RedisBroker(MessageBrokerInterface):
    def __init__(self):
        super().__init__()
        self.client: aioredis.Redis = None

    async def connect(self, temp: str = None):
        async_redis_connection_pool = aioredis.ConnectionPool(
            host='localhost')
        self.client = aioredis.Redis.from_pool(async_redis_connection_pool)

    async def disconnect(self):
        await self.client.close()

    async def delete_message(self, message_id: str):
        await self.client.delete(message_id)

    async def subscribe(self, topic: str):
        self.pubsub = self.client.pubsub()
        await self.pubsub.subscribe(topic)

    async def unsubscribe(self, topic: str):
        if self.pubsub is not None:
            await self.pubsub.unsubscribe(topic)

    async def listen(self) -> AsyncGenerator[str, None]:
        async for message in self.pubsub.listen():
            # print(f"(Reader) Message Received: {message}")
            if message['type'] == 'message':
                yield message['data']

    async def publish(self, topic: str, message: any):
        await self.client.publish(topic, message)

    async def send_request(
        self,
        queue: str,
        message: ArbiterMessage,
    ):
        await self.client.rpush(queue, message.encode())

    async def send_request_and_wait_for_response(
        self,
        queue: str,
        message: ArbiterMessage,
        timeout=3,  # sec
    ) -> ArbiterMessage | None:
        """
            현재는 한 서비스에서 한번에 1개의 메세지만 보낼 수 있다.
        """
        # print("Sending request and waiting for response")
        # print(f"Queue: {queue}, Message: {message}")
        # 요청 데이터를 Redis에 게시
        await self.client.rpush(queue, message.encode())
        # 응답 대기 (최대 5초)
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = await self.client.get(message.from_service_id)
            if response:
                await self.client.delete(message.from_service_id)
                return ArbiterMessage.decode(response)
            time.sleep(0.1)
        return None
