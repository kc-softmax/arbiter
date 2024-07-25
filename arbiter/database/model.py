from typing import Optional, Type
from pydantic import BaseModel, Field
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
    state: ServiceState
    is_master: bool
    ip_address: str
    shutdown_code: str
    created_at: datetime
    updated_at: datetime

class ServiceMeta(DefaultModel):
    node_id: int
    module_name: str
    
class TaskFunction(DefaultModel):
    queue_name: str
    service_meta: ServiceMeta
    
class HttpTaskFunction(TaskFunction):
    method: HttpMethod | None = Field(default=None)
    request_models: str | None = Field(default=None)
    response_model: str | None = Field(default=None)
    
class StreamTaskFunction(TaskFunction):
    connection: StreamMethod | None = Field(default=None)
    communication_type: StreamCommunicationType | None = Field(default=None)
    num_of_channels: int = Field(default=1)    
    
class Service(DefaultModel):
    node_id: int
    state: ServiceState
    created_at: datetime
    updated_at: datetime
    service_meta: ServiceMeta
    description: Optional[str] = Field(default=None)