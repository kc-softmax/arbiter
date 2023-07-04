from fastapi import FastAPI
from database import create_db_and_tables
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .auth.router import router as auth_router, login
from .exceptions import BadRequest
from .utils import update_openapi_schema_name

app = FastAPI()


def create_custom_openapi():
    if not app.openapi_schema:
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
        )
        for _, method_item in app.openapi_schema.get('paths').items():
            for _, param in method_item.items():
                responses = param.get('responses')
                # remove 422 response, also can remove other status code
                if '422' in responses:
                    del responses['422']

    return app.openapi_schema


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
