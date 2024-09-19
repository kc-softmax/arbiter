from __future__ import annotations
import json
import time
import uuid
import pickle
import asyncio
import redis.asyncio as aioredis
from pydantic import BaseModel
from datetime import timezone, datetime
from redis.asyncio.client import PubSub
from typing import AsyncGenerator, Any, Callable, TypeVar, Optional, Type, get_args
from arbiter.utils import is_optional_type, restore_type, to_snake_case, get_pickled_data
from arbiter.data.models import ArbiterTaskModel, DefaultModel
from arbiter.exceptions import ArbiterDecodeError, AribterEncodeError
from arbiter.constants import ASYNC_TASK_CLOSE_MESSAGE, DEFAULT_CONFIG

T = TypeVar('T', bound=DefaultModel)

class Arbiter:
    
    async_redis_connection_pool = None
    
    def __init__(
        self,
        name: str,
        host: str = "localhost", 
        port: int = 6379, 
        config: dict = {}
    ):
        # __new__에서 생성된 인스턴스의 초기화 작업을 여기서 진행
        self.name = name
        self.host = host
        self.port = port
        self.config = DEFAULT_CONFIG
        self.config.update(config)
        self.client: aioredis.Redis = None
        self.keep_alive_task: asyncio.Task = None
        self.pubsub_map: dict[str, PubSub] = {}

        # Redis 클라이언트 초기화
        if not Arbiter.async_redis_connection_pool:
            if password := self.config.get("aribter_password", None):
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
        return await self.client.delete(f'{table_name}:{model_data.get_id()}')

    async def save_data(self, model_data: T) -> T:
        table_name = to_snake_case(model_data.__class__.__name__)
        if hasattr(model_data, 'updated_at'):
            setattr(model_data, 'updated_at', datetime.now(timezone.utc))
        await self.client.set(
            f'{table_name}:{model_data.get_id()}', model_data.model_dump_json()
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
    async def request_packer(
        self,
        parameters: dict,
        *args, 
        **kwargs
    ):
        # TODO Pass model parameter
        # validate model? not yet
        assert len(args) == 0 or len(kwargs) == 0, "currently, args and kwargs cannot be used together"
        data: list | dict = None
        if len(args) > 0:
            data = []
            for arg in args:
                # assert isinstance(arg, (str, int, float, bool)), "args must be str, int, float, bool"
                if isinstance(arg, BaseModel):
                    data.append(arg.model_dump())
                else:
                    data.append(arg)
        elif len(kwargs) > 0:
            data = {}
            for key, value in kwargs.items():
                # assert isinstance(value, (str, int, float, bool)), "args must be str, int, float, bool"
                if isinstance(value, BaseModel):
                    data[key] = value.model_dump()
                else:
                    data[key] = value
        else:
            data = None
            
        return data
    
    async def results_unpacker(self, return_type: Any, results: Any):
        if is_optional_type(return_type):
            if results is None:
                return None
            return_type = get_args(return_type)[0]
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            results = return_type.model_validate_json(results)
        return results
    
    ################ task management ################
    async def get_task_return_and_parameters(self, task_queue: str):
        task_model = await self.get_data(ArbiterTaskModel, task_queue)
        parameter_dict: dict = json.loads(task_model.transformed_parameters)
        parameters = {
            k: (restore_type(v), ...)
            for k, v in parameter_dict.items()
        }
        return_type = restore_type(json.loads(task_model.transformed_return_type))
        return parameters, return_type
    
    async def async_task(self, target: str, *args, **kwargs):
        parameters, return_type = await self.get_task_return_and_parameters(target)
        data = await self.request_packer(
            parameters,
            *args,
            **kwargs
        )

        message_id = await self.send_message(
            target=target,
            data=data
        )
        if not return_type:
            return None 
        results = await self.get_message(message_id)
        if isinstance(results, Exception):
            raise results
        return await self.results_unpacker(return_type, results)


    async def async_stream_task(self, target: str, *args, **kwargs):
        parameters, return_type = await self.get_task_return_and_parameters(target)
        data = await self.request_packer(
            parameters,
            *args,
            **kwargs
        )

        message_id = await self.send_message(
            target=target,
            data=data
        )
        async for results in self.get_stream(message_id):
            yield await self.results_unpacker(return_type, results)

    ################ message management ################
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
    
    async def get_message(
        self,
        message_id: str,
        timeout: float = None,
    ) -> Any | None:
        if not timeout:
            timeout = self.config.get("arbiter_send_timeout")
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
            return e
        except Exception as e:
            print(f"Error in getting response from {message_id}: {e})")
        return None

    async def get_stream(
        self,
        message_id: str,
        timeout: float = None,
    ) -> Any | None:
        if not timeout:
            timeout = self.config.get("arbiter_send_timeout")
        try:
            async for data in self.listen(message_id, timeout):
                if not data:
                    continue
                pickled_data = get_pickled_data(data)
                if pickled_data is not None:
                    yield pickled_data
                else:
                    yield data.decode()
        except asyncio.CancelledError:
            pass
        except TimeoutError as e:
            raise e
        except Exception as e:
            raise e
        
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
                # TODO Change return Exception
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
    ) -> AsyncGenerator[list[bytes], None]:
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
                    collected_messages.append(response[1])
            if collected_messages:
                yield collected_messages
            else:
                # 주기 동안 메시지가 없더라도 빈 리스트를 반환
                yield []