from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from server.exceptions import BadRequest
from server.utils import FastAPIWrapper
from server.database import create_db_and_tables
from server.auth.router import router as auth_router, login
from reference.router import router as reference_router

app_wrapper = FastAPIWrapper()

app = app_wrapper()
app.include_router(auth_router)
app.include_router(reference_router)

# customize swagger schema
# it should be done after all routers are included
app_wrapper.update_openapi_schema_name(login, "LoginRequest")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=BadRequest.STATUS_CODE, content={"detail": BadRequest.DETAIL})


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
