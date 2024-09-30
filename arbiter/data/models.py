from __future__ import annotations
import uuid
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from arbiter.enums import (
    NodeState,
)

############################################
    
class ArbiterBaseNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
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
class ArbiterNode(ArbiterBaseNode):

    def get_health_check_channel(self) -> str:
        return f"__health_check__{self.id}"
        
    def get_system_channel(self) -> str:
        return f"__system__{self.id}"

    def get_routing_channel(self) -> str:
        return f"__routing__{self.id}"
    
############################################
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
class ArbiterServiceNode(ArbiterBaseNode):
    arbiter_node_id: str
    # 만약 지정된 gateway가 없다면, 모든 gateway에 등록
    gateway_node_id: Optional[str] = Field(default='')
    task_node_ids: list[str] = Field(default_factory=list)
    description: Optional[str] = Field(default='')
    
############################################
class ArbiterTaskNode(ArbiterBaseNode):
    service_node_id: str
    queue: str
    service_name: str
    transformed_parameters: str = Field(default='')
    transformed_return_type: str = Field(default='')
    task_nodes: list[ArbiterTaskNode] = Field(default_factory=list)

    # for http task
    http: bool = Field(default=False)
    stream: bool = Field(default=False)
    file: bool = Field(default=False)
    request: bool = Field(default=False)
        
    def get_id(self) -> str:
        return self.queue
    
    def __eq__(self, other: ArbiterTaskNode) -> bool:
        return self.queue == other.queue

