# pyright: reportUndefinedVariable=false

from fastapi import FastAPI
from typing import Callable


def update_openapi_schema_name(app: FastAPI, function: Callable, name: str) -> None:
    for route in app.routes:
        if route.endpoint is function:
            route.body_field.type_.__name__ = name
            return


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


def exceptions_to_openapi_response(code: int, detail: str) -> dict:
    response = {}
    response[code] = {
        "content": {
            "application/json": {
                "example": {"detail": detail}
            }
        }
    }
    return response
