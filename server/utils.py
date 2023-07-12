from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel.main import SQLModelMetaclass
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware

from server.logging import log_middleware


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
    def __init__(self) -> None:
        self.app = FastAPI()
        # self.app.openapi = self.create_custom_openapi
        self.app.add_middleware(
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
        self.app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)

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


class Omit(SQLModelMetaclass):
    def __new__(self, name, bases, namespaces, **kwargs):
        omit_fields = getattr(namespaces.get("Config", {}), "omit_fields", {})
        fields = namespaces.get('__fields__', {})
        annotations = namespaces.get('__annotations__', {})
        for base in bases:
            fields.update(base.__fields__)
            annotations.update(base.__annotations__)
        merged_keys = fields.keys() & annotations.keys()
        [merged_keys.add(field) for field in fields]
        new_fields = {}
        new_annotations = {}
        for field in merged_keys:
            if not field.startswith('__') and field not in omit_fields:
                new_annotations[field] = annotations.get(field, fields[field].type_)
                new_fields[field] = fields[field]
        namespaces['__annotations__'] = new_annotations
        namespaces['__fields__'] = new_fields
        return super().__new__(self, name, bases, namespaces, **kwargs)


class Pick(SQLModelMetaclass):
    def __new__(self, name, bases, namespaces, **kwargs):
        pick_fields = getattr(namespaces.get("Config", {}), "pick_fields", {})
        fields = namespaces.get('__fields__', {})
        annotations = namespaces.get('__annotations__', {})
        for base in bases:
            fields.update(base.__fields__)
            annotations.update(base.__annotations__)
        merged_keys = fields.keys() & annotations.keys()
        [merged_keys.add(field) for field in fields]
        new_fields = {}
        new_annotations = {}
        for field in merged_keys:
            if not field.startswith('__') and field in pick_fields:
                new_annotations[field] = annotations.get(field, fields[field].type_)
                new_fields[field] = fields[field]
        namespaces['__annotations__'] = new_annotations
        namespaces['__fields__'] = new_fields
        return super().__new__(self, name, bases, namespaces, **kwargs)


class AllOptional(SQLModelMetaclass):
    def __new__(self, name, bases, namespaces, **kwargs):
        annotations = namespaces.get('__annotations__', {})
        for base in bases:
            annotations.update(base.__annotations__)
        for field in annotations:
            if not field.startswith('__'):
                annotations[field] = Optional[annotations[field]]
        namespaces['__annotations__'] = annotations
        return super().__new__(self, name, bases, namespaces, **kwargs)
