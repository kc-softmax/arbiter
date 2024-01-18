from typing import AsyncGenerator, Tuple, TypeVar, Generic, Protocol
import redis.asyncio as aioredis
import asyncio

from redis.asyncio.client import Redis

# 추상화 모음
T = TypeVar('T')

# 메시지 브로커 클라이언트 인터페이스
class MessageBrokerInterface(Protocol, Generic[T]):
    client: T
    producer: "MessageProducerInterface"
    consumer: "MessageConsumerInterface"

    def __init__(self, client: T) -> None:
        super().__init__()
        self.client =  client

    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError
    
    async def generate(self) -> Tuple["MessageBrokerInterface", "MessageProducerInterface", "MessageConsumerInterface"]:
        raise NotImplementedError
    
    async def __aenter__(self) -> Tuple["MessageBrokerInterface", "MessageProducerInterface", "MessageConsumerInterface"]:
        await self.connect()
        await self.generate()
        await self.consumer.__aenter__()
        return self, self.producer, self.consumer

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.consumer.__aexit__()
        await self.disconnect()

# Producer 인터페이스
class MessageProducerInterface(Generic[T]):
    def __init__(self, client: T):
        self.client = client

    async def send(self, topic: str, message: str):
        raise NotImplementedError

# Consumer 인터페이스
class MessageConsumerInterface(Generic[T]):
    def __init__(self, client: T):
        self.client = client

    async def subscribe(self, topic: str):
        raise NotImplementedError

    async def listen(self) -> AsyncGenerator[str, None]:
        raise NotImplementedError
    
##############################################
# 레디스 클라이언트 설정 및 생성
# TODO like make_async_session?
async_redis_connection_pool = aioredis.ConnectionPool(host="localhost")

class RedisBroker(MessageBrokerInterface[aioredis.Redis]):
    def __init__(self):
        self.client: aioredis.Redis = None

    async def connect(self):
        self.client = aioredis.Redis(connection_pool=async_redis_connection_pool)

    async def disconnect(self):
        await self.client.aclose()
    
    async def generate(self) -> Tuple[MessageBrokerInterface, MessageProducerInterface, MessageConsumerInterface]:
        self.producer = RedisMessageProducer(self.client)
        self.consumer = RedisMessageConsumer(self.client)
        return self, self.producer, self.consumer

class RedisMessageProducer(MessageProducerInterface[aioredis.Redis]):
    async def send(self, topic: str, message: str):
        await self.client.publish(topic, message)
    
class RedisMessageConsumer(MessageConsumerInterface[aioredis.Redis]):
    def __init__(self, client: Redis):
        super().__init__(client)
        self.pubsub = None

    async def subscribe(self, topic: str):
        self.pubsub = self.client.pubsub()
        await self.pubsub.subscribe(topic)

    async def listen(self) -> AsyncGenerator[str, None]:
        async for message in self.pubsub.listen():
            print(f"(Reader) Message Received: {message}")
            if message['type'] == 'message':
                yield message['data']

    async def __aenter__(self):
        return self

    async def __aexit__(self):
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()

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
    # TODO move to shutdown
    await async_redis_connection_pool.disconnect()
        
asyncio.run(main())