from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from arbiter.api.auth.router import router as auth_router
from arbiter.api.database import async_engine
from arbiter.api.exceptions import BadRequest
from arbiter.api.config import settings


class ArbiterApp(FastAPI):
    def __init__(self) -> None:
        super().__init__()
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

    async def on_shutdown(self):
        await async_engine.dispose()

arbiterApp = ArbiterApp()
