import asyncio
import pickle

from functools import wraps
from typing import Awaitable, Callable
from fastapi import APIRouter, FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from arbiter.constants import (
    ARBITER_SERVICE_HEALTH_CHECK_INTERVAL,
    ARBITER_SERVICE_TIMEOUT,
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_SYSTEM_QUEUE,
    ArbiterMessageType,
    ArbiterMessage
)
from arbiter.api.auth.router import router as auth_router
from arbiter.api.exceptions import BadRequest
from arbiter.api.stream import ArbiterStream

from arbiter.broker import RedisBroker


class ArbiterApp(FastAPI):
    def __init__(self) -> None:
        super().__init__()
        self.add_event_handler("startup", self.on_startup)
        self.add_event_handler("shutdown", self.on_shutdown)
        self.add_exception_handler(
            RequestValidationError,
            lambda request, exc: JSONResponse(
                status_code=BadRequest.STATUS_CODE,
                content={"detail": BadRequest.DETAIL}
            )
        )
        self.add_middleware(
            CORSMiddleware,
            allow_origins='*',
            allow_credentials=True,
            allow_methods='*',
            allow_headers='*'
        )
        # app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)
        self.include_router(auth_router)
        self.broker: RedisBroker = None
        # registered_functions[path] = wrapper
        self.registered_functions: dict[
            str, Callable[[dict], Awaitable[dict]]] = {}
        self.services_router: dict[str, APIRouter] = {}
        self.stream_handlers: dict[str, Callable[[
            ArbiterStream], Awaitable[None]]] = {}

    async def on_startup(self):
        # NOTE(24.06.13) temp_chat_service.py를 테스트 실행 하기 위한 임시 주석
        # self.redis_broker = await RedisBroker.create()
        pass
        # start system event consumer
        # if initialize broker failed, raise exception or warning

    async def on_shutdown(self):
        # NOTE(24.06.13) temp_chat_service.py를 테스트 실행 하기 위한 임시 주석
        # await self.redis_broker.close()
        pass

    def stream(self, path: str) -> Callable[[Callable[[ArbiterStream], Awaitable[None]]], None]:
        async def connect_stream(websocket: WebSocket, token: str = Query()):
            stream = await ArbiterStream.create(websocket, token, self.broker)
            try:
                await self.stream_handlers[path](stream)  # 스트림 핸들러 호출
            except Exception as e:
                print(f"WebSocket connection error: {e}")
            finally:
                if websocket.client_state is WebSocketState.CONNECTED:
                    # show warning message that we recommend to close connection in stream
                    await websocket.close()

        def decorator(handler: Callable[[ArbiterStream], Awaitable[None]]) -> None:
            self.stream_handlers[path] = handler
            self.websocket(path)(connect_stream)

        return decorator

    def add_service_route(self, service_name: str, path: str, endpoint: Callable[[], Awaitable[None]]):
        if self.services_router.get(service_name) is None:
            self.services_router[service_name] = APIRouter(
                prefix=f"/services/{service_name}")
            self.include_router(self.services_router[service_name])

        router = self.services_router[service_name]

        @router.post(path)
        async def publish(data: dict):
            await self.broker.producer.send(
                service_name,
                pickle.dumps(data))
            return {"message": f"Request sent to {path} function."}


arbiterApp = ArbiterApp()


# def register_service_route(service_name: str, path: str):

#     def decorator(func):
#         @ wraps(func)
#         async def wrapper(data: dict):
#             return func(data)

#         # 함수 등록
#         arbiterApp.registered_functions[path] = wrapper
#         # FastAPI 라우터에 경로 추가
#         arbiterApp.add_service_route(service_name, path)

#         return wrapper
#     return decorator
