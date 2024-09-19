from __future__ import annotations
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from arbiter.enums import (
    NodeState,
)

############################################
class DefaultModel(BaseModel):
    #abstarct
    
    def get_id(self) -> str:
        raise NotImplementedError()

class ArbiterBaseModel(DefaultModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    
    def get_id(self) -> str:
        return self.id    
    
class ArbiterBaseNode(DefaultModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_model_id: str
    state: NodeState
    shutdown_code: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_id(self) -> str:
        return self.id
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: ArbiterBaseNode) -> bool:
        return self.id == other.id
    

############################################
class ArbiterNodeModel(ArbiterBaseModel):
    # master policy?
    # some configuration
    pass

class ArbiterNode(ArbiterBaseNode):
    gateway_node_ids: list[str] = Field(default_factory=list)
    service_node_ids: list[str] = Field(default_factory=list)

    def get_health_check_channel(self) -> str:
        return f"__health_check__{self.id}"
        
    def get_system_channel(self) -> str:
        return f"__system__{self.id}"

    def get_routing_channel(self) -> str:
        return f"__routing__{self.id}"
    
############################################
class ArbiterGatewayModel(ArbiterBaseModel):
    arbiter_node_model_id: str

class ArbiterGatewayNode(ArbiterBaseNode):
    arbiter_node_id: str
    host: str
    port: int
    log_level: str
    allow_origins: str
    allow_methods: str
    allow_headers: str
    allow_credentials: bool

############################################
class ArbiterServiceModel(ArbiterBaseModel):
    arbiter_node_model_id: str
    gateway_model_id: Optional[str] = Field(default='')
    module_name: str
    num_of_services: int
    auto_start: bool
    task_model_ids: list[str] = Field(default_factory=list)
    
    def get_service_name(self) -> str:
        return f"{self.name}_{self.id}"
    
    def get_service_channel(self) -> str:
        return f"__service__{self.get_service_name()}"

class ArbiterServiceNode(ArbiterBaseNode):
    arbiter_node_id: str
    task_node_ids: list[str] = Field(default_factory=list)
    description: Optional[str] = Field(default=None)
    
############################################
class ArbiterTaskModel(ArbiterBaseModel):
    queue: str
    service_model_id: str
    service_name: str
    transformed_parameters: str = Field(default='')
    transformed_return_type: str = Field(default='')
    http: bool = Field(default=False)
    stream: bool = Field(default=False)
    task_nodes: list[ArbiterTaskNode] = Field(default_factory=list)
        
    def get_id(self) -> str:
        return self.queue
    
    def __eq__(self, other: ArbiterTaskModel) -> bool:
        return self.queue == other.queue

class ArbiterTaskNode(ArbiterBaseNode):
    service_node_id: str



# class ArbiterTaskModel(DefaultModel):
#     service_meta: ServiceMeta
#     num_of_tasks: int
#     cold_start: bool = Field(default=False)
#     raw_message: bool = Field(default=False)
#     retry_count: int = Field(default=0)
#     activate_duration: int = Field(default=0)
#     queue: str = Field(default='')
#     params: str = Field(default='')
#     response: str = Field(default='')
#     interval: int = Field(default=0)
#     channel: str = Field(default='')
#     method: int = Field(default=0)
#     connection_info: bool = Field(default=False)
#     connection: int = Field(default=0)
#     communication_type: int = Field(default=0)
#     num_of_channels: int = Field(default=1)
