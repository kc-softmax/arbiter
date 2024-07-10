from typing import Optional
from pydantic import BaseModel, Field, PrivateAttr
from datetime import datetime
from arbiter.constants.enums import (
    ServiceState, 
    HttpMethod, 
    StreamMethod,
    StreamCommunicationType
)


class DefaultModel(BaseModel):
    id: int
    name: Optional[str] = Field(default=None)
    
class Node(DefaultModel):
    unique_id: str
    is_master: bool
    ip_address: str
    shutdown_code: str
    created_at: datetime
    updated_at: datetime

    def __str__(self):
        return self.unique_id
        
class User(DefaultModel):
    email: str
    password: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = Field(default=None)
    access_token: Optional[str] = Field(default=None)
    refresh_token: Optional[str] = Field(default=None)


class ServiceMeta(DefaultModel):
    module_name: str

class Service(DefaultModel):
    state: ServiceState
    created_at: datetime
    updated_at: datetime
    service_meta: ServiceMeta
    description: Optional[str] = Field(default=None)

class TaskFunction(DefaultModel):
    queue_name: str
    parameters: list[tuple[str, str]]
    service_meta: ServiceMeta
    channel: str = Field(default=None)
    period: float = Field(default=None)
    auth: bool = Field(default=False)
    routing: bool = Field(default=False)
    method: HttpMethod | None = Field(default=None)
    timeout: int = Field(default=None)
    connection: StreamMethod | None = Field(default=None)
    communication_type: StreamCommunicationType | None = Field(default=None)
    