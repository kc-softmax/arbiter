from __future__ import annotations
import time
import asyncio
import redis.asyncio as aioredis
from datetime import timezone, datetime
from redis.asyncio.client import PubSub
from typing import AsyncGenerator, Any, TypeVar, Optional, Type
from arbiter.database.model import DefaultModel
from arbiter.utils import to_snake_case, get_pickled_data
from arbiter.exceptions import ArbiterTimeOutError, ArbiterDecodeError
from arbiter.constants import (
    ARIBTER_DEFAULT_TASK_TIMEOUT,
    ASYNC_TASK_CLOSE_MESSAGE,
)
from arbiter.constants.messages import (
    ArbiterMessage,
)

T = TypeVar('T', bound=DefaultModel)

class Arbiter:
    
    async_redis_connection_pool = None
    
    def __init__(self):
        super().__init__()
        self.client: aioredis.Redis = None
        self.keep_alive_task: asyncio.Task = None
        self.pubsub_map: dict[str, PubSub] = {}

    def __new__(cls):
        if not cls.async_redis_connection_pool:
            from arbiter.core import CONFIG_FILE
            from arbiter.core.utils import read_config
            config = read_config(CONFIG_FILE)
            host = config.get("cache", "redis.url", fallback="localhost")
            port = config.get("cache", "redis.port", fallback="6379")
            password = config.get("cache", "redis.password", fallback=None)
            if password:
                redis_url = f"redis://:{password}@{host}:{port}/"
            else:
                redis_url = f"redis://{host}:{port}/"
            cls.async_redis_connection_pool = aioredis.ConnectionPool.from_url(redis_url)
            return super().__new__(cls)

    async def connect(self):
        self.client = aioredis.Redis.from_pool(self.async_redis_connection_pool)
        self.keep_alive_task = asyncio.create_task(self.keep_alive())
        
    async def get_client(self):
        return aioredis.Redis.from_pool(self.async_redis_connection_pool)

    async def keep_alive(self):
        while True:
            try:
                await self.client.ping()
                await asyncio.sleep(20)
            except aioredis.ConnectionError:
                print("Redis 연결이 끊겼습니다. 재연결합니다...")
                self.connect()

    async def disconnect(self):
        if self.keep_alive_task:
            self.keep_alive_task.cancel()
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
        data: str | bytes,
        wait_response: bool = False,
        timeout: float = ARIBTER_DEFAULT_TASK_TIMEOUT,
    ):
        message = ArbiterMessage(data=data)
        
        await self.client.rpush(receiver_id, message.model_dump_json())
        if not wait_response:
            return None
        try:
            response_data = await self.client.blpop(message.id, timeout=timeout)
        except Exception as e:
            print(f"Error in getting response from {receiver_id}: {e}")
        if response_data:
            pickle_data = get_pickled_data(response_data[1])
            if pickle_data is not None:
                return pickle_data
            return response_data[1].decode()
        else:
            response_data = None
        # TODO MARK Test ref check
        await self.delete_message(message.id)
        return response_data

    async def push_message(self, target: str, message: Any):
        if message is None:
            return
        await self.client.rpush(target, message)

    async def get_message(self, queue: str, timeout: int = ARIBTER_DEFAULT_TASK_TIMEOUT) -> bytes:
        response_data = await self.client.blpop(queue, timeout=timeout)
        if response_data:
            return response_data[1]
        raise TimeoutError(f"Timeout in getting message from {queue}")

    async def delete_message(self, message_id: str):
        await self.client.delete(message_id)

    async def remove_message(self, queue: str, message: str):
        await self.client.lrem(queue, 0, message)

    async def subscribe_listen(
        self,
        channel: str,
        pubsub_id: str = None
    ) -> AsyncGenerator[str, None]:
        # arbiter에서 사용되는 pubsub은 시스템 종료시 리소스를 반환한다
        # pubsub 객체를 따로 관리하지 않는다
        pubsub = self.client.pubsub()
        if pubsub_id:
            self.pubsub_map[pubsub_id] = pubsub
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
        while True:
            message = await self.client.blpop(channel, timeout)
            if message:
                if message[1] == ASYNC_TASK_CLOSE_MESSAGE:
                    break
                yield message[1]
            else:
                raise ArbiterTimeOutError(f"Timeout in getting message from {channel}")

    async def listen(
        self,
        channel: str,
        timeout: int = 0
    ) -> AsyncGenerator[
        Optional[ArbiterMessage],
        None
    ]:
        while True:
            message = await self.client.blpop(channel, timeout)
            if message:
                try:
                    yield ArbiterMessage.model_validate_json(message[1])
                except Exception as e:
                    raise ArbiterDecodeError(f"Error in decoding message: {e}")
            else:
                raise ArbiterTimeOutError(f"Timeout in getting message from {channel}")

    async def periodic_listen(
        self,
        queue: str,
        interval: float = 1
    ) -> AsyncGenerator[list[ArbiterMessage], None]:
        while True:
            collected_messages = []
            start_time = time.monotonic()
            while (time.monotonic() - start_time) < interval:
                # 현재 시간과 시작 시간의 차이를 계산하여 timeout을 조정
                timeout = interval - (time.monotonic() - start_time)
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