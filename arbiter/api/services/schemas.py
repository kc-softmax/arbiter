from sqlalchemy import Column, String
from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    service_id: int
    target_registry_ids: list[int] = []
    message: bytes


class FetchServiceListSchema(BaseModel):
    service_id: int | None = None


class StartServiceSchema(BaseModel):
    service_id: int


class ManageSchema(BaseModel):
    service_name: str
    service_ids: list[str] | None = None


class ServiceRegistrySchema(BaseModel):
    id: int
    state: str
    service_run_time: float


class ServiceSchema(BaseModel):
    id: int
    name: str
    registered_services: list[ServiceRegistrySchema] = []
