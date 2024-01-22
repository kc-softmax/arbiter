from __future__ import annotations
from typing import AsyncGenerator, Tuple
import asyncio
import redis.asyncio as aioredis

from arbiter.broker.base import MessageBrokerInterface, MessageConsumerInterface, MessageProducerInterface

# TODO like make_async_session??
async_redis_connection_pool = aioredis.ConnectionPool(host="localhost")


class RedisBroker(MessageBrokerInterface[aioredis.Redis]):
    def __init__(self):
        self.client: aioredis.Redis = None

    async def connect(self):
        self.client = aioredis.Redis(
            connection_pool=async_redis_connection_pool)

    async def disconnect(self):
        await self.client.close()

    async def generate(self) -> Tuple[MessageBrokerInterface, MessageProducerInterface, MessageConsumerInterface]:
        self.producer = RedisMessageProducer(self.client)
        self.consumer = RedisMessageConsumer(self.client)
        return self, self.producer, self.consumer


class RedisMessageProducer(MessageProducerInterface[aioredis.Redis]):
    async def send(self, topic: str, message: str):
        await self.client.publish(topic, message)


class RedisMessageConsumer(MessageConsumerInterface[aioredis.Redis]):
    def __init__(self, client: aioredis.Redis):
        super().__init__(client)
        self.pubsub = None

    async def subscribe(self, topic: str):
        self.pubsub = self.client.pubsub()
        await self.pubsub.subscribe(topic)

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


# asyncio task로 넣을 때
# async def reader(consumer: MessageConsumerInterface):
#     while True:
#         async for message in consumer.listen():
#             if message is not None:
#                 print(f"(Reader) Message Received: {message}")
#                 break

async def main():
    async with RedisBroker() as (broker, producer, consumer):
        await consumer.subscribe('test_channel')

        await producer.send('test_channel', 'Hello, Redis!')
        # await asyncio.create_task(consumer.listen())
        async for message in consumer.listen():
            print(f"Received message: {message}")
            break
    # # TODO move to shutdown
    await async_redis_connection_pool.disconnect()

# asyncio.run(main())
