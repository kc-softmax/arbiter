from __future__ import annotations
import time
import uuid
import pickle
import redis.asyncio as aioredis
from datetime import timezone, datetime
from redis.asyncio.client import PubSub
from typing import AsyncGenerator, Any, TypeVar, Optional, Type
from arbiter.database.model import DefaultModel
from arbiter.utils import to_snake_case
from arbiter.constants import (
    ARIBTER_DEFAULT_TASK_TIMEOUT,
)
from arbiter.constants.messages import (
    ArbiterMessage,
)

T = TypeVar('T', bound=DefaultModel)

class Arbiter:
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.client: aioredis.Redis = None
        self.pubsub_map: dict[str, PubSub] = {}

    async def connect(self):
        from arbiter.cli import CONFIG_FILE
        from arbiter.cli.utils import read_config
        config = read_config(CONFIG_FILE)
        host = config.get("cache", "redis.url", fallback="localhost")
        port = config.get("cache", "cache", fallback="6379")
        redis_url = f"redis://{host}:{port}/{self.name}"
        self.async_redis_connection_pool = aioredis.ConnectionPool.from_url(redis_url)
        self.client = aioredis.Redis.from_pool(self.async_redis_connection_pool)

    async def disconnect(self):
        await self.async_redis_connection_pool.disconnect()
        await self.async_redis_connection_pool.aclose()

    async def initialize(self):
        await self.clear_database()

    async def clear_database(self):
        await self.client.flushdb()

    ################ generic management ################
    async def get_next_id(self, table_name: str) -> int:
        # Redis INCR 명령을 사용하여 auto_increment 구현
        return await self.client.incr(f'{table_name}:id_counter')
    
    async def get_data(self, model_class: Type[T], id: int) -> Optional[T]:
        table_name = to_snake_case(model_class.__name__)
        data = await self.client.get(f'{table_name}:{id}')
        if data:
            return model_class.model_validate_json(data)
        return None

    async def create_data(self, model_class: Type[T], **kwargs) -> T:
        table_name = to_snake_case(model_class.__name__)
        new_id = await self.get_next_id(table_name)
        data = model_class(
            id=new_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            **kwargs,
        )
        await self.client.set(f'{table_name}:{data.id}', data.model_dump_json())
        return data

    async def update_data(
        self,
        data: T,
        **kwargs
    ) -> Optional[T]:
        table_name = to_snake_case(data.__class__.__name__)
        for k, v in kwargs.items():
            if hasattr(data, k):
                setattr(data, k, v)
        if hasattr(data, 'updated_at'):
            setattr(data, 'updated_at', datetime.now(timezone.utc))
        await self.client.set(f'{table_name}:{data.id}', data.json())
        return data

    async def search_data(self, model_class: Type[T], **kwargs) -> list[T]:
        table_name = to_snake_case(model_class.__name__)
        results = []
        keys = [
            key
            for key in await self.client.keys(f"{table_name}:*")
            if b'id_counter' not in key
        ]
        for key in keys:
            data = await self.client.get(key)
            if data:
                model_data = model_class.model_validate_json(data)
                conditions: list[bool] = []
                for index_field, value in kwargs.items():
                    conditions.append(
                        hasattr(model_data, index_field) and getattr(model_data, index_field) == value
                    )
                # if all conditions is true then append to results
                if all(conditions):
                    results.append(model_data)
        return results

    async def send_message(
        self,
        receiver_id: str,
        message: ArbiterMessage,
        response_with_pickle: bool = True,
        timeout: float = ARIBTER_DEFAULT_TASK_TIMEOUT,
    ):
        await self.client.rpush(receiver_id, message.model_dump_json())
        if not message.response:
            return None
        try:
            response_data = await self.client.blpop(message.id, timeout=timeout)
        except Exception as e:
            print(f"Error in getting response from {receiver_id}: {e}")
        if response_data:
            if response_with_pickle:
                response_data = pickle.loads(response_data[1])
            else:
                response_data = response_data[1].decode()
        else:
            response_data = None
        # TODO MARK Test ref check
        await self.delete_message(message.id)
        return response_data

    async def push_message(self, target: str, message: Any):
        await self.client.rpush(target, message)

    async def get_message(self, queue: str, timeout: int = ARIBTER_DEFAULT_TASK_TIMEOUT) -> bytes:
        response_data = await self.client.blpop(queue, timeout=timeout)
        if response_data:
            return response_data[1]
        raise TimeoutError(f"Timeout in getting message from {queue}")

    async def delete_message(self, message_id: str):
        await self.client.delete(message_id)

    async def subscribe(
        self,
        channel: str,
        managed: bool = False
    ) -> AsyncGenerator[str, None]:
        # pubsub이 생성되고 id를 생성한 후에 구독 시작
        pubsub = self.client.pubsub()
        if managed:
            pubsub_id = uuid.uuid4().hex
            self.pubsub_map[pubsub_id] = pubsub
            yield pubsub_id

        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield message['data']

    async def punsubscribe(self, pusbusb_id: str):
        if self.pubsub_map.get(pusbusb_id):
            await self.pubsub_map[pusbusb_id].punsubscribe("*")
            await self.pubsub_map[pusbusb_id].aclose()
            self.pubsub_map.pop(pusbusb_id)

    async def broadcast(
        self,
        topic: str, 
        message: str | bytes,
    ):
        await self.client.publish(topic, message)

    async def listen_bytes(
        self,
        channel: str,
        timeout: int = 0
    ) -> AsyncGenerator[
        bytes,
        None
    ]:
        try:
            while True:
                message = await self.client.blpop(channel, timeout)
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
        channel: str,
        timeout: int = 0
    ) -> AsyncGenerator[
        Optional[ArbiterMessage],
        None
    ]:
        try:
            while True:
                message: Optional[tuple[str, str]] = await self.client.blpop(channel, timeout)
                if message:
                    yield ArbiterMessage.model_validate_json(message[1])
                else:
                    yield None
        except Exception as e:
            print('error in : ', e)
            yield None

    async def periodic_listen(
        self,
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
                response = await self.client.blpop(queue, timeout=1)
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