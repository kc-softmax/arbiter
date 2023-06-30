from fastapi import FastAPI
from database import create_db_and_tables
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth.router import router as auth_router, login
from .exceptions import BadRequest
from .utils import update_openapi_schema_name, create_custom_openapi

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=BadRequest.STATUS_CODE, content={"detail": BadRequest.DETAIL})


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# add routers
app.include_router(auth_router)

# customize swagger schema
app.openapi = create_custom_openapi
update_openapi_schema_name(app, login, "LoginRequest")
