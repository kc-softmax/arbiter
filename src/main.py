from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from database import create_db_and_tables

from .auth.router import router as auth_router, login
from .exceptions import BadRequest
from .utils import FastAPIWrapper

app_wrapper = FastAPIWrapper()
# customize swagger schema
app_wrapper.update_openapi_schema_name(login, "LoginRequest")


app = app_wrapper()
app.include_router(auth_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=BadRequest.STATUS_CODE, content={"detail": BadRequest.DETAIL})


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
