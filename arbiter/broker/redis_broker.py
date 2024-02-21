from __future__ import annotations
from typing import AsyncGenerator, Tuple
import redis.asyncio as aioredis

from arbiter.broker.base import MessageBrokerInterface, MessageConsumerInterface, MessageProducerInterface

class RedisBroker(MessageBrokerInterface):
    def __init__(self):
        super().__init__()
        self.client: aioredis.Redis = None

    async def connect(self):
        async_redis_connection_pool = aioredis.ConnectionPool(host="localhost")
        self.client = aioredis.Redis.from_pool(async_redis_connection_pool)

    async def disconnect(self):
        await self.client.close()

    async def generate(self) -> Tuple[MessageBrokerInterface, MessageProducerInterface, MessageConsumerInterface]:
        self.producer = RedisMessageProducer(self.client)
        self.consumer = RedisMessageConsumer(self.client)
        return self, self.producer, self.consumer


class RedisMessageProducer(MessageProducerInterface):
    def __init__(self, client: aioredis.Redis) -> None:
        super().__init__()
        self.client = client

    async def send(self, topic: str, message: str):
        await self.client.publish(topic, message)


class RedisMessageConsumer(MessageConsumerInterface):
    def __init__(self, client: aioredis.Redis):
        super().__init__()
        self.client = client
        self.pubsub = None

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

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
