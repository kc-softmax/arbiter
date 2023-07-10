from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth.router import router as auth_router, login
from .exceptions import BadRequest
from .utils import FastAPIWrapper
from database import create_db_and_tables


app_wrapper = FastAPIWrapper()

app = app_wrapper()
app.include_router(auth_router)

# customize swagger schema
# it should be done after all routers are included
app_wrapper.update_openapi_schema_name(login, "LoginRequest")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=BadRequest.STATUS_CODE, content={"detail": BadRequest.DETAIL})


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
