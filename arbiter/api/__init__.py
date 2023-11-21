from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from arbiter.api.auth.router import router as auth_router
from arbiter.api.database import create_db_and_tables, async_engine
from arbiter.api.exceptions import BadRequest
from arbiter.api.live.service import LiveService

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
            allow_origins=[
                "*",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.include_router(auth_router)

    async def on_startup(self):
        await create_db_and_tables()
    
    async def on_shutdown(self):
        await async_engine.dispose()
        
    def add_live_service(self, path:str, 
                         service: LiveService):
        async def connect(websocket: WebSocket, token: str = Query()):
            async with service.connect(websocket, token) as [user_id, user_name]:
                await service.publish_to_engine(websocket, user_id, user_name)
        self.add_api_websocket_route(path, connect)

arbiterApp = ArbiterApp()
