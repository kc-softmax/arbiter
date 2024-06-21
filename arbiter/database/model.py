from pydantic import BaseModel, Field
from datetime import datetime
from arbiter.constants.enums import ServiceState


class DefaultModel(BaseModel):
    id: int = Field(
        default_factory=lambda: DefaultModel._generate_id(), init=False)

    _id_counter: int = 0

    @classmethod
    def _generate_id(cls):
        cls._id_counter += 1
        return cls._id_counter


class ServiceMeta(DefaultModel):
    name: str


class Service(DefaultModel):
    state: ServiceState
    created_at: datetime
    updated_at: datetime
    service_meta: ServiceMeta


class RpcFunction(DefaultModel):
    name: str
    queue_name: str
    service_meta: ServiceMeta
