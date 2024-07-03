from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from datetime import datetime
from arbiter.constants.enums import ServiceState, HttpMethod, StreamMethod


class DefaultModel(BaseModel):
    id: int = Field(
        default_factory=lambda: DefaultModel._generate_id(), init=False)

    _id_counter: int = PrivateAttr(default=0)

    @classmethod
    def _generate_id(cls):
        cls._increment_id_counter()
        return cls._id_counter

    @classmethod
    def _increment_id_counter(cls):
        if isinstance(cls._id_counter, int):
            cls._id_counter += 1
        else:
            cls._id_counter = 1


class User(DefaultModel):
    email: str
    password: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None)
    refresh_token: Optional[str] = Field(default=None)


class ServiceMeta(DefaultModel):
    name: str
    module_name: str
    initial_processes: int


class Service(DefaultModel):
    state: ServiceState
    created_at: datetime
    updated_at: datetime
    service_meta: ServiceMeta
    description: Optional[str] = Field(default=None)


class TaskFunction(DefaultModel):
    name: str
    queue_name: str
    parameters: list[tuple[str, str]]
    service_meta: ServiceMeta
    auth: bool = Field(default=False)
    method: HttpMethod | None = Field(default=None)
    connection: StreamMethod | None = Field(default=None)
