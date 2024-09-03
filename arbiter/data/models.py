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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class ArbiterBaseModel(DefaultModel):
    name: str
    
class ArbiterBaseNode(DefaultModel):
    state: NodeState
    shutdown_code: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

############################################
class ArbiterModel(ArbiterBaseModel):
    # master policy?
    # some configuration
    service_models: list[ArbiterServiceModel] = Field(default_factory=list)
    server_models: list[ArbiterServerModel] = Field(default_factory=list)

class ArbiterNode(ArbiterBaseNode):
    arbiter_model_id: str
    is_master: bool
    server_nodes: list[ArbiterServerNode] = Field(default_factory=list)
    service_nodes: list[ArbiterServiceNode] = Field(default_factory=list)

    def get_health_check_channel(self) -> str:
        return f"__health_check__{self.id}"
        
    def get_system_channel(self) -> str:
        return f"__system__{self.id}"

    def get_routing_channel(self) -> str:
        return f"__routing__{self.id}"
    
############################################
class ArbiterServerModel(ArbiterBaseModel):
    arbiter_model_id: str
    num_of_services: int = Field(default=1)
    http_task_models: list[ArbiterHttpTaskModel] = Field(default_factory=list)
    stream_task_models: list[ArbiterStreamTaskModel] = Field(default_factory=list)

class ArbiterServerNode(ArbiterBaseNode):
    arbiter_node_id: str
    arbiter_server_model_id: str

############################################
class ArbiterServiceModel(ArbiterBaseModel):
    module_name: str
    auto_start: bool = Field(default=False)
    num_of_services: int = Field(default=1)
    task_models: list[ArbiterTaskModel] = Field(default_factory=list)
    async_task_models: list[ArbiterAsyncTaskModel] = Field(default_factory=list)
    http_task_models: list[ArbiterHttpTaskModel] = Field(default_factory=list)
    stream_task_models: list[ArbiterStreamTaskModel] = Field(default_factory=list)
    periodic_task_models: list[ArbiterPeriodicTaskModel] = Field(default_factory=list)
    subscribe_task_models: list[ArbiterSubscribeTaskModel] = Field(default_factory=list)
    
    def get_service_name(self) -> str:
        return f"{self.name}_{self.id}"
    
    def get_service_channel(self) -> str:
        return f"__service__{self.get_service_name()}"

class ArbiterServiceNode(ArbiterBaseNode):
    arbiter_node_id: str
    arbiter_service_model_id: str
    description: Optional[str] = Field(default=None)
    
############################################
class ArbiterTaskModel(ArbiterBaseModel):
    service_name: str
    num_of_tasks: int
    queue: str
    params: str = Field(default='')
    response: str = Field(default='')
    activate_duration: int = Field(default=0)
    cold_start: bool = Field(default=False)
    raw_message: bool = Field(default=False)
    retry_count: int = Field(default=0)
    task_nodes: list[ArbiterTaskNode] = Field(default_factory=list)

class ArbiterAsyncTaskModel(ArbiterTaskModel):
    # async task model, 나누는 이유는 검사를 위해
    pass

class ArbiterHttpTaskModel(ArbiterTaskModel):
    # http task model, 나누는 이유는 검사를 위해
    method: int = Field(default=0)

class ArbiterStreamTaskModel(ArbiterTaskModel):
    connection: int = Field(default=0)
    communication_type: int = Field(default=0)
    num_of_channels: int = Field(default=1)

class ArbiterPeriodicTaskModel(ArbiterTaskModel):
    interval: int = Field(default=0)
    
class ArbiterSubscribeTaskModel(ArbiterTaskModel):
    channel: str = Field(default='')

class ArbiterTaskNode(ArbiterBaseNode):
    model: ArbiterTaskModel
    service_node: ArbiterServiceNode
    pass
#     task_meta: TaskMeta
#     shutdown_code: str = Field(default_factory=lambda: str(uuid.uuid4()))
#     description: Optional[str] = Field(default=None)
    
#     def get_task_name(self) -> str:
#         return f"{self.task_meta.name}_{self.id}"
    
#     def get_task_channel(self) -> str:
#         return f"__task__{self.get_task_name()}"


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
