from __future__ import annotations
import time
import pickle
import redis.asyncio as aioredis
from warnings import warn
from pydantic import BaseModel
from redis.asyncio.client import PubSub
from typing import AsyncGenerator, Any
from arbiter.broker.base import MessageBrokerInterface
from arbiter.constants import (
    ARIBTER_DEFAULT_TASK_TIMEOUT,
)
from arbiter.constants.messages import (
    ArbiterMessage,
)

class RedisBroker(MessageBrokerInterface):
    def __init__(self, name: str):
        super().__init__()
        from arbiter.cli import CONFIG_FILE
        from arbiter.cli.utils import read_config
        self.name = name
        config = read_config(CONFIG_FILE)
        host = config.get("cache", "redis.url", fallback="localhost")
        port = config.get("cache", "cache", fallback="6379")
        redis_url = f"redis://{host}:{port}/{self.name}"
        self.async_redis_connection_pool = aioredis.ConnectionPool.from_url(redis_url)

    async def connect(self) -> aioredis.Redis:
        client = aioredis.Redis.from_pool(self.async_redis_connection_pool)
        return client

    async def disconnect(self, client: aioredis.Redis):
        if client:
            await client.aclose()

    async def send_message(
        self,
        client: aioredis.Redis,
        receiver_id: str,
        message: ArbiterMessage,
        timeout: float = ARIBTER_DEFAULT_TASK_TIMEOUT
    ):
        await client.rpush(receiver_id, message.model_dump_json())
        if not message.response:
            return None
        response_data = await client.blpop(message.id, timeout=timeout)
        if response_data:
            response_data = response_data[1].decode()
        else:
            response_data = None
        # TODO MARK Test ref check
        await self.delete_message(client, message.id)
        return response_data

    async def push_message(self, client: aioredis.Redis, target: str, message: Any):
        await client.rpush(target, message)

    async def get_message(self, client: aioredis.Redis, queue: str, timeout: int = ARIBTER_DEFAULT_TASK_TIMEOUT) -> bytes:
        response_data = await client.blpop(queue, timeout=timeout)
        if response_data:
            return response_data[1]
        raise TimeoutError(f"Timeout in getting message from {queue}")

    async def delete_message(self, client: aioredis.Redis, message_id: str):
        await client.delete(message_id)

    async def subscribe(
        self,
        client: aioredis.Redis,
        channel: str
    ) -> AsyncGenerator[str, None]:
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield message['data']
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()

    async def broadcast(
        self,
        client: aioredis.Redis,
        topic: str, 
        message: str | bytes,
    ):
        await client.publish(topic, message)

    async def listen_bytes(
        self,
        client: aioredis.Redis,
        channel: str,
        timeout: int = 0
    ) -> AsyncGenerator[
        bytes,
        None
    ]:
        try:
            while True:
                message = await client.blpop(channel, timeout)
                if message:
                    yield message[1]
                else:
                    yield None
        except Exception as e:
            print('error in : ', e)
            yield None
        print('end')

    async def listen(
        self,
        client: aioredis.Redis,
        channel: str,
        timeout: int = 0
    ) -> AsyncGenerator[
        ArbiterMessage,
        None
    ]:
        try:
            while True:
                message = await client.blpop(channel, timeout)
                if message:
                    yield ArbiterMessage.model_validate_json(message[1])
                else:
                    yield None
        except Exception as e:
            print('error in : ', e)
            yield None

    async def periodic_listen(
        self,
        client: aioredis.Redis,
        queue: str,
        period: float = 1
    ) -> AsyncGenerator[list[ArbiterMessage], None]:
        while True:
            collected_messages = []
            start_time = time.monotonic()
            while (time.monotonic() - start_time) < period:
                # 현재 시간과 시작 시간의 차이를 계산하여 timeout을 조정
                timeout = period - (time.monotonic() - start_time)
                if timeout <= 0:
                    break
                # 비동기적으로 메시지를 가져옴
                response = await client.blpop(queue, timeout=1)
                if response:
                    message = ArbiterMessage.model_validate_json(response[1])
                else:
                    message = None
                if message:
                    # 메시지가 있으면 수집하고 continue로 다시 시도
                    collected_messages.append(message)
                    continue
            if collected_messages:
                yield collected_messages
            else:
                # 주기 동안 메시지가 없더라도 빈 리스트를 반환
                yield []
