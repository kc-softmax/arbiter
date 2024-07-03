from __future__ import annotations
import inspect
import redis.asyncio as aioredis
from typing import Callable, Optional, TypeVar, Type
from datetime import datetime, UTC
from arbiter.utils import to_snake_case, extract_annotation
from arbiter.constants.enums import ServiceState, HttpMethod, StreamMethod
from arbiter.constants.protocols import (
    HttpTaskProtocol,
    StreamTaskProtocol,
    SubscribeTaskProtocol,
    PeriodicTaskProtocol,
)
from arbiter.database.model import (
    DefaultModel,
    User,
    Service,
    TaskFunction,
    ServiceMeta)

T = TypeVar('T', bound=DefaultModel)

# env or config에 따라서 다르게 생성되게 해야할까?
# engine을 따로 만들어서 사용하는 것이 좋을까?


class Database:
    # get singleton instance
    _instance = None

    @classmethod
    def get_db(cls) -> Database:
        if cls._instance is None:
            cls._instance = Database()
        return cls._instance

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

    ################ generic management ################
    async def get_data(self, id: int, model_class: Type[T]) -> Optional[T]:
        table_name = to_snake_case(model_class.__name__)
        data = await self.client.get(f'{table_name}:{id}')
        if data:
            return model_class.parse_raw(data)
        return None

    async def create_data(self, model_class: Type[T], **kwargs) -> T:
        table_name = to_snake_case(model_class.__name__)
        data = model_class(
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
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
            data.updated_at = datetime.now(UTC)
        await self.client.set(f'{table_name}:{data.id}', data.json())
        return data

    ################ user management ################
    async def get_user_from_email(self, email: str) -> User | None:
        keys = await self.client.keys(f'user:*')
        for key in keys:
            data = await self.client.get(key)
            if data:
                user = User.parse_raw(data)
                if user.email == email:
                    return user
        return None
    ################ service management ################

    async def fetch_service_meta(self, name: str = '') -> list[ServiceMeta]:
        keys = await self.client.keys(f'service_meta:{name}*')
        service_metas = []
        for key in keys:
            data = await self.client.get(key)
            if data:
                service_metas.append(ServiceMeta.parse_raw(data))
        return service_metas

    async def find_services(self, states: list[ServiceState]) -> list[Service]:
        keys = await self.client.keys(f'service:*')
        services = []
        for key in keys:
            data = await self.client.get(key)
            if data:
                service = Service.parse_raw(data)
                if not states:
                    services.append(service)
                elif service.state in states:
                    services.append(service)
        return services

    async def fetch_task_functions(self, service: ServiceMeta = None) -> list[TaskFunction]:
        keys = await self.client.keys(f'task_function:*')
        task_functions = []
        for key in keys:
            data = await self.client.get(key)
            if data:
                task_function = TaskFunction.parse_raw(data)
                if service is None or task_function.service_meta.id == service.id:
                    task_functions.append(task_function)
        return task_functions

    async def create_service_meta(
        self,
        service_name: str,
        service_module_name: str,
        tasks: list[HttpTaskProtocol | StreamTaskProtocol],
        initial_processes: int,
    ) -> ServiceMeta:
        service_meta = ServiceMeta(
            name=service_name,
            module_name=service_module_name,
            initial_processes=initial_processes
        )
        await self.client.set(f'service_meta:{service_meta.name}', service_meta.json())
        for task in tasks:
            queue_name = f'{to_snake_case(
                service_name)}_{task.__name__}'
            signature = inspect.signature(task)
            # Print the parameters of the function
            # check if the first argument is User instance
            parameters = [
                (param.name, extract_annotation(param))
                for param in signature.parameters.values()
                if param.name != 'self'
            ]
            task_function = TaskFunction(
                name=task.__name__,
                queue_name=queue_name,
                service_meta=service_meta,
                parameters=parameters,
                auth=getattr(task, 'auth', False),
                method=getattr(task, 'method', None),
                connection=getattr(task, 'connection', None),
            )
            await self.client.set(f'task_function:{task_function.id}', task_function.json())
        return service_meta
