import asyncio
import uvicorn
from fastapi import APIRouter, FastAPI
from arbiter.broker import periodic_task
from arbiter.database import Database, ServiceMeta, RpcFunction
from arbiter.service.redis_service import RedisService
from arbiter.constants.enums import ArbiterMessageType
from arbiter.constants.data import ArbiterMessage


class ApiService(RedisService):

    def __init__(self, app: FastAPI, server: uvicorn.Server):
        super().__init__()
        self.db = Database()
        self.app = app
        self.app.on_event("startup")(self.on_startup)
        self.app.on_event("shutdown")(self.on_shutdown)
        self.server = server
        self.services_routers: dict[str, APIRouter] = {}

    @classmethod
    async def launch(cls, **kwargs):
        app = FastAPI()
        router = APIRouter()

        app.include_router(router)
        config = uvicorn.Config(
            app,
            host=kwargs.get('host', '0.0.0.0'),
            port=kwargs.get('port', 8080),
            log_level='error',
        )

        server = uvicorn.Server(config)
        instance = cls(app, server)
        asyncio.create_task(server.serve())
        service = asyncio.create_task(instance.start())
        result = await service
        return result

    async def shutdown(
        self,
        dynamic_tasks: list[asyncio.Task],
    ):
        await self.db.disconnect()
        await self.server.shutdown()
        await super().shutdown(dynamic_tasks)

    async def on_startup(self):
        await self.db.connect()
        rpc_funcs = await self.db.fetch_rpc_functions()
        for rpc_func in rpc_funcs:
            self.add_service_rpc_to_router(rpc_func.service_meta, rpc_func)
        # self.add_service_rpc_to_router(rpc_func.service_name, rpc_func.func_name)
        # start system event consumer
        # if initialize broker failed, raise exception or warning

    async def on_shutdown(self):
        pass
        # await PrismaClientWrapper.disconnect()

    def add_service_rpc_to_router(
        self,
        service_meta: ServiceMeta,
        rpc_func: RpcFunction,
    ):
        service_name = service_meta.name.lower()
        rpc_func_name = rpc_func.name
        if service_name not in self.services_routers:
            self.services_routers[service_name] = APIRouter(
                prefix=f"/services/{service_name}")
            self.app.include_router(self.services_routers[service_name])

        router = self.services_routers[service_name]

        @router.post(f'/{rpc_func_name}')
        async def publish(data: dict):
            response = await self.broker.send_message(
                rpc_func.queue_name,
                data
            )
            return {"message": f"{response}"}

    @periodic_task(period=1)
    async def manage_rpc_func(self, messages: list[bytes]):
        """
            1초에 한번씩, 새로운 rpc 함수가 있으면 등록하고, 기존에 등록된 rpc 함수를 점검한다.
        """
        if messages:
            pass
            # print(f"Api Service received message: {messages}")
            # self.add_service_rpc_to_router("test", "test_func")
            # for message in messages:
            #     match message.type:
            #         case ArbiterMessageType.API_ROUTE_REGISTER:
            #             # 함수명,
            #             print(f"Service {message.data} registered")
            #             pass
            #         case ArbiterMessageType.API_ROUTE_UNREGISTER:
            #             await self.handle_service_unregistered(message.data)

    async def handle_service_unregistered(self, service_id: str):
        pass
        # print(f"Service {service_id} unregistered")

    async def get_message(self, message: bytes):
        pass

    async def service_work(self) -> bool:
        # log를 처리한다.
        return True
