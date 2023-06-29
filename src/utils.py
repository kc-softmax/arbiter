from fastapi import FastAPI
from typing import Callable


def update_openapi_schema_name(app: FastAPI, function: Callable, name: str) -> None:
    for route in app.routes:
        if route.endpoint is function:
            route.body_field.type_.__name__ = name
            return


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
