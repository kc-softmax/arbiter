import uuid
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
    state: ServiceState
    is_master: bool
    ip_address: str
    unique_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    shutdown_code: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime
    updated_at: datetime

class ServiceMeta(DefaultModel):
    node_id: int
    module_name: str
    
class TaskFunction(DefaultModel):
    auth: bool = Field(default=False)
    service_meta: ServiceMeta
    task_queue: str = Field(default='')
    task_params: str = Field(default='')
    task_response: str = Field(default='')

class HttpTaskFunction(TaskFunction):
    method: HttpMethod | None = Field(default=None)
    
class StreamTaskFunction(TaskFunction):
    connection: StreamMethod | None = Field(default=0)
    communication_type: StreamCommunicationType | None = Field(default=0)
    num_of_channels: int = Field(default=1)    
    
class Service(DefaultModel):
    node_id: int
    state: ServiceState
    created_at: datetime
    updated_at: datetime
    service_meta: ServiceMeta
    description: Optional[str] = Field(default=None)