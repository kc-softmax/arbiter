from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Callable

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


class FastAPIWrapper:
    def __init__(self):
        self.app = FastAPI()
        self.app.openapi = self.create_custom_openapi

    def __call__(self):
        return self.app

    def update_openapi_schema_name(self, function: Callable, name: str) -> None:
        for route in self.app.routes:
            if route.endpoint is function:
                route.body_field.type_.__name__ = name
                return

    def create_custom_openapi(self):
        if not self.app.openapi_schema:
            self.app.openapi_schema = get_openapi(
                title=self.app.title,
                version=self.app.version,
                openapi_version=self.app.openapi_version,
                description=self.app.description,
                terms_of_service=self.app.terms_of_service,
                contact=self.app.contact,
                license_info=self.app.license_info,
                routes=self.app.routes,
                tags=self.app.openapi_tags,
                servers=self.app.servers,
            )
        for _, method_item in self.app.openapi_schema.get('paths').items():
            for _, param in method_item.items():
                responses = param.get('responses')
                # remove 422 response, also can remove other status code
                if '422' in responses:
                    del responses['422']
        return self.app.openapi_schema
