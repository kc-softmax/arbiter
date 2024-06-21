from __future__ import annotations
import redis.asyncio as aioredis
from datetime import datetime, UTC
from typing import Callable, Optional
from arbiter.constants.enums import ServiceState
from arbiter.database.model import (
    Service,
    RpcFunction,
    ServiceMeta
)


# env or config에 따라서 다르게 생성되게 해야할까?
# engine을 따로 만들어서 사용하는 것이 좋을까?
class Database:

    client: aioredis.Redis = None

    def __init__(self):
        self.client: aioredis.Redis = None

    async def connect(self):
        async_redis_connection_pool = aioredis.ConnectionPool(
            host='localhost', port=6379)
        self.client = aioredis.Redis.from_pool(async_redis_connection_pool)

    async def disconnect(self):
        await self.client.close()

    async def initialize(self):
        await self.clear_database()

    async def clear_database(self):
        await self.client.flushdb()

    async def get_service_meta(self, name: str) -> ServiceMeta:
        data = await self.client.get(f'service_meta:{name}')
        if data:
            return ServiceMeta.parse_raw(data)
        return None

    async def fetch_service_meta(self, name: str = '') -> list[ServiceMeta]:
        keys = await self.client.keys(f'service_meta:{name}*')
        service_metas = []
        for key in keys:
            data = await self.client.get(key)
            if data:
                service_metas.append(ServiceMeta.parse_raw(data))
        return service_metas

    async def find_services(self, state: ServiceState) -> list[Service]:
        keys = await self.client.keys(f'service:*')
        services = []
        for key in keys:
            data = await self.client.get(key)
            if data:
                service = Service.parse_raw(data)
                if service.state == state:
                    services.append(service)
        return services

    async def get_service(self, service_id: int) -> Service | None:
        data = await self.client.get(f'service:{service_id}')
        if not data:
            return None
        return Service.parse_raw(data)

    async def create_service(self, service_meta: ServiceMeta) -> Service:
        service = Service(
            state=ServiceState.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            service_meta=service_meta
        )
        await self.client.set(f'service:{service.id}', service.json())
        return service

    async def update_service(self, service_id: int, state: Optional[ServiceState] = None) -> Optional[Service]:
        data = await self.client.get(f'service:{service_id}')
        if not data:
            return None
        service = Service.parse_raw(data)
        if state:
            service.state = state
        service.updated_at = datetime.now(UTC)
        await self.client.set(f'service:{service.id}', service.json())
        return service

    async def fetch_rpc_functions(self, service: ServiceMeta = None) -> list[RpcFunction]:
        keys = await self.client.keys(f'rpc_function:*')
        rpc_functions = []
        for key in keys:
            data = await self.client.get(key)
            if data:
                rpc_function = RpcFunction.parse_raw(data)
                if service is None or rpc_function.service_meta.id == service.id:
                    rpc_functions.append(rpc_function)
        return rpc_functions

    async def create_service_meta(self, service_name: str, rpc_funcs: list[Callable]) -> ServiceMeta:
        service_meta = ServiceMeta(name=service_name)
        await self.client.set(f'service_meta:{service_meta.name}', service_meta.json())
        for rpc_func in rpc_funcs:
            queue_name = f'{service_meta.name.lower()}_{rpc_func.__name__}'
            rpc_function = RpcFunction(
                name=rpc_func.__name__, queue_name=queue_name, service_meta=service_meta)
            await self.client.set(f'rpc_function:{rpc_function.id}', rpc_function.json())
        return service_meta
