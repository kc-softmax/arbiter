from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from server.exceptions import BadRequest
from server.database import create_db_and_tables, async_engine
from server.logging import log_middleware
from server.auth.router import router as auth_router
from server.chat.router import router as chat_router


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)
app.include_router(auth_router)
app.include_router(chat_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=BadRequest.STATUS_CODE, content={"detail": BadRequest.DETAIL})


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()


# 가비지 pool 쌓이는 것을 방지
@app.on_event("shutdown")
async def on_shutdown():
    await async_engine.dispose()
