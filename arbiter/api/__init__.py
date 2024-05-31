from typing import Awaitable, Callable
from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState

from arbiter.api.auth.router import router as auth_router
from arbiter.api.exceptions import BadRequest
from arbiter.api.config import settings
from arbiter.api.stream import ArbiterStream

from arbiter.broker.redis_broker import RedisBroker


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
            allow_origins=settings.ALLOW_ORIGINS,
            allow_credentials=settings.ALLOW_ORIGINS,
            allow_methods=settings.ALLOW_METHODS,
            allow_headers=settings.ALLOW_HEADERS,
        )
        # app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)
        self.include_router(auth_router)
        self.redis_broker: RedisBroker = None
        self.stream_handlers: dict[str, Callable[[
            ArbiterStream], Awaitable[None]]] = {}

    async def on_startup(self):
        self.redis_broker = await RedisBroker.create()
        # start system event consumer
        # if initialize broker failed, raise exception or warning

    async def on_shutdown(self):
        await self.redis_broker.close()

    def stream(self, path: str) -> Callable[[Callable[[ArbiterStream], Awaitable[None]]], None]:
        async def connect_stream(websocket: WebSocket, token: str = Query()):
            stream = await ArbiterStream.create(websocket, token, self.redis_broker)
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


arbiterApp = ArbiterApp()
