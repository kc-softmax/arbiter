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
    master_id: int
    ip_address: str
    unique_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    shutdown_code: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def system_channel(cls, node_id: str) -> str:
        return f"__system__{node_id}"
    
    @classmethod
    def routing_channel(cls, node_id: str) -> str:
        return f"__routing__{node_id}"
    
    def get_system_channel(self) -> str:
        return f"__system__{self.unique_id}"
    
    def get_routing_channel(self) -> str:
        return f"__routing__{self.unique_id}"
        
class ServiceMeta(DefaultModel):
    node_id: int
    from_master: bool
    module_name: str
    auto_start: bool = Field(default=False)

class Service(DefaultModel):
    node_id: int
    state: ServiceState
    created_at: datetime
    updated_at: datetime
    service_meta: ServiceMeta
    shutdown_code: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = Field(default=None)
    
    def get_service_name(self) -> str:
        return f"{self.service_meta.name}_{self.id}"

class WebService(DefaultModel):
    node_id: str
    app_id: str
    state: ServiceState
    created_at: datetime
    updated_at: datetime

class WebServiceTask(DefaultModel):
    web_service_id: int
    task_id: int
    created_at: datetime
    updated_at: datetime

class ArbiterTaskModel(DefaultModel):
    service_meta: ServiceMeta
    num_of_tasks: int
    cold_start: bool = Field(default=False)
    raw_message: bool = Field(default=False)
    retry_count: int = Field(default=0)
    activate_duration: int = Field(default=0)
    queue: str = Field(default='')
    params: str = Field(default='')
    response: str = Field(default='')
    interval: int = Field(default=0)
    channel: str = Field(default='')
    method: int = Field(default=0)
    connection_info: bool = Field(default=False)
    connection: int = Field(default=0)
    communication_type: int = Field(default=0)
    num_of_channels: int = Field(default=1)
