from __future__ import annotations
import time
import uuid
import pickle
import asyncio
import redis.asyncio as aioredis
from pydantic import BaseModel
from datetime import timezone, datetime
from redis.asyncio.client import PubSub
from typing import AsyncGenerator, Any, Callable, TypeVar, Optional, Type
from arbiter.utils import to_snake_case, get_pickled_data
from arbiter.data.models import DefaultModel
from arbiter.exceptions import ArbiterDecodeError, AribterEncodeError
from arbiter.constants import (
    ARBITER_SEND_TIMEOUT,
    ARBITER_GET_TIMEOUT,
    ASYNC_TASK_CLOSE_MESSAGE,
)

T = TypeVar('T', bound=DefaultModel)

class Arbiter:
    
    async_redis_connection_pool = None
    
    def __init__(
        self,
        host: str = "localhost", 
        port: int = 6379, 
        password: str = None
    ):
        # __new__에서 생성된 인스턴스의 초기화 작업을 여기서 진행
        self.client: aioredis.Redis = None
        self.keep_alive_task: asyncio.Task = None
        self.pubsub_map: dict[str, PubSub] = {}

        # Redis 클라이언트 초기화
        if not Arbiter.async_redis_connection_pool:
            if password:
                redis_url = f"redis://:{password}@{host}:{port}/"
            else:
                redis_url = f"redis://{host}:{port}/"
            Arbiter.async_redis_connection_pool = aioredis.ConnectionPool.from_url(redis_url)
        
        self.client = aioredis.Redis(connection_pool=Arbiter.async_redis_connection_pool)

    def __new__(cls, *args, **kwargs):
        if not cls.async_redis_connection_pool:
            # 새로운 인스턴스를 생성하고 반환
            instance = super(Arbiter, cls).__new__(cls)
            return instance
        else:
            # 이미 인스턴스가 생성된 경우, 기존 인스턴스를 반환
            return super(Arbiter, cls).__new__(cls)
        
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
                await self.connect()

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
    async def get_data(self, model_class: Type[T], id: str) -> Optional[T]:
        table_name = to_snake_case(model_class.__name__)
        data = await self.client.get(f'{table_name}:{id}')
        if data:
            return model_class.model_validate_json(data)
        return None

    async def delete_data(self, model_data: T) -> bool:
        table_name = to_snake_case(model_data.__class__.__name__)
        return await self.client.delete(f'{table_name}:{model_data.id}')

    async def save_data(self, model_data: T) -> T:
        table_name = to_snake_case(model_data.__class__.__name__)
        if hasattr(model_data, 'updated_at'):
            setattr(model_data, 'updated_at', datetime.now(timezone.utc))
                
        await self.client.set(
            f'{table_name}:{model_data.id}', model_data.model_dump_json()
        )
        return model_data

    async def search_data(self, model_class: Type[T], **kwargs) -> list[T]:
        table_name = to_snake_case(model_class.__name__)
        results = []
        for key in await self.client.keys(f"{table_name}:*"):
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
    ################################################    
    async def encode_message(self, data: Any) -> bytes:
        message_id = uuid.uuid4().hex
        return message_id, pickle.dumps((message_id, data))

    async def push_message(self, target: str, message: Any):
        if message is None:
            return
        await self.client.rpush(target, message)

    async def delete_message(self, message_id: str):
        await self.client.delete(message_id)

    async def remove_message(self, queue: str, message: str):
        await self.client.lrem(queue, 0, message)

    async def send_message(
        self,
        target: str,
        data: str | bytes,
    ) -> str | None:
        try:
            message_id, encoded_message = await self.encode_message(data)
        except Exception as e:
            raise AribterEncodeError(f"Error in encoding message: {e}")
        
        try:
            # target validation?
            await self.client.rpush(target, encoded_message)
            return message_id
        except Exception as e:
            await self.remove_message(target, encoded_message)
        return None
        
        
        #     _, raw_data = response
        #     pickled_data = get_pickled_data(raw_data)
        #     if pickled_data is not None:
        #         return pickled_data
        #     # fail to pickle data
        #     return raw_data.decode()
        # except TimeoutError as e:
        #     print(f"Timeout in getting response from {target}: {e}")
        # except Exception as e:
        #     print(f"Error in getting response from {target}: {e}")

    async def get_message(
        self,
        message_id: str,
        timeout: float = ARBITER_SEND_TIMEOUT,
    ) -> Any | None:
        try:
            response = await self.client.blpop(message_id, timeout)
            if response:
                _, data = response
                pickled_data = get_pickled_data(data)
                if pickled_data is not None:
                    return pickled_data
                # fail to pickle data, maybe it is a string
                return data.decode()
        except TimeoutError as e:
            print(f"Timeout in getting response from {message_id}: {e}")
        except Exception as e:
            print(f"Error in getting response from {message_id}: {e})")
        return None

    async def get_stream(
        self,
        message_id: str,
        timeout: float = ARBITER_SEND_TIMEOUT
    ) -> Any | None:
        try:
            async for data in self.listen(message_id, timeout):
                pickled_data = get_pickled_data(data)
                if pickled_data is not None:
                    yield pickled_data
                # fail to pickle data, maybe it is a string
                yield data.decode()
        except asyncio.CancelledError:
            pass
        except TimeoutError as e:
            print(f"Timeout in getting response from {message_id}: {e}")
        except Exception as e:
            print(f"Error in getting response from {message_id}: {e})")
        
    async def listen(
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
                raise TimeoutError(f"Timeout in getting message from {channel}")

    async def subscribe_listen(
        self,
        channel: str,
        pubsub_id: str = None
    ) -> AsyncGenerator[bytes, None]:
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