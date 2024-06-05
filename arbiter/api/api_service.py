import asyncio
from typing import Awaitable, Callable
import uvicorn

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from arbiter.api.auth.router import router as auth_router
from arbiter.api.exceptions import BadRequest
from arbiter.database import PrismaClientWrapper
from arbiter.service import AbstractService
from arbiter.broker import RedisBroker


class ApiService(AbstractService[RedisBroker]):

    def __init__(self, app: FastAPI, server: uvicorn.Server):
        super().__init__(RedisBroker, frequency=0.1)
        self.app = app
        self.server = server

    @ classmethod
    def launch(cls, **kwargs):
        app = FastAPI()
        app.include_router(auth_router)
        config = uvicorn.Config(
            app,
            host=kwargs.get('host', '0.0.0.0'),
            port=kwargs.get('port', 8011),
        )

        server = uvicorn.Server(config)
        instance = cls(app, server)
        api_loop = asyncio.new_event_loop()
        service_loop = asyncio.new_event_loop()
        tasks = [
            api_loop.run_in_executor(None, server.run),
            service_loop.run_until_complete(instance.service_start())
        ]
        loop = asyncio.new_event_loop()
        loop.run_until_complete(*tasks)

    async def service_stop(self):
        print("ApiService stop")
        await self.server.shutdown()
        super().service_stop()

    async def on_startup(self):
        await PrismaClientWrapper.connect()

        # start system event consumer
        # if initialize broker failed, raise exception or warning

    async def on_shutdown(self):
        await PrismaClientWrapper.disconnect()

    async def handle_service_unregistered(self, service_id: str):
        print(f"Service {service_id} unregistered")

    async def get_message(self, message: bytes):
        pass

    async def service_work(self) -> bool:
        # log를 처리한다.
        return True
