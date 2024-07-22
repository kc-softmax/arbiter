from __future__ import annotations
import redis.asyncio as aioredis
from typing import Optional, TypeVar, Type
from datetime import datetime, timezone
from arbiter.utils import to_snake_case
from arbiter.database.model import (
    DefaultModel,
    User,
    TaskFunction,
    Node
)

T = TypeVar('T', bound=DefaultModel)

# env or config에 따라서 다르게 생성되게 해야할까?
# engine을 따로 만들어서 사용하는 것이 좋을까?


class Database:
    # get singleton instance
    _instance_maps: dict[str, Database] = {}

    @classmethod
    def get_db(cls, name: str) -> Database:
        if name not in cls._instance_maps:
            cls._instance_maps[name] = Database(name)
        return cls._instance_maps[name]

    def __init__(self, name: str):
        self.name = name
        self.client: aioredis.Redis = None

    async def connect(self):
        from arbiter.cli import CONFIG_FILE
        from arbiter.cli.utils import read_config
        config = read_config(CONFIG_FILE)
        host = config.get("cache", "redis.url", fallback="localhost")
        port = config.get("cache", "cache", fallback="6379")
        redis_url = f"redis://{host}:{port}/{self.name}"
        async_redis_connection_pool = aioredis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True
        )
        self.client = aioredis.Redis.from_pool(async_redis_connection_pool)

    async def disconnect(self):
        await self.client.aclose()

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
            return model_class.parse_raw(data)
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
        await self.client.set(f'{table_name}:{data.id}', data.json())
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
            if 'id_counter' not in key
        ]
        for key in keys:
            data = await self.client.get(key)
            if data:
                model_data = model_class.parse_raw(data)
                conditions: list[bool] = []
                for index_field, value in kwargs.items():
                    conditions.append(
                        hasattr(model_data, index_field) and getattr(model_data, index_field) == value
                    )                        
                # if all conditions is true then append to results
                if all(conditions):
                    results.append(model_data)
        return results
    
     ################ User management ################
    async def fetch_user_channels(self, user_ids: list[int]) -> list[str]:
        results = []
        keys = [
            f'user:{user_id}'
            for user_id in user_ids
        ]
        values = await self.client.mget(*keys)
        for value in values:
            if value:
                data = User.model_validate_json(value)
                results.append(data)
        return results