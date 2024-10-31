from __future__ import annotations
import uuid
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from arbiter.enums import (
    NodeState,
)

############################################
    
class ArbiterBaseNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default='')
    state: NodeState
    shutdown_code: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_id(self) -> str:
        return self.node_id
    
    def encode_node_state(self) -> dict[str, Any]:
        return  {
            'node_id': self.get_id(),
            'state': self.state,
        }
    
    def __hash__(self) -> int:
        return hash(self.node_id)
    
    def __eq__(self, other: ArbiterBaseNode) -> bool:
        return self.node_id == other.node_id
    

############################################
class ArbiterNode(ArbiterBaseNode):

    def get_health_check_channel(self) -> str:
        return f"__health_check__{self.node_id}"
        
    def get_system_channel(self) -> str:
        return f"__system__{self.node_id}"

    def get_routing_channel(self) -> str:
        return f"__routing__{self.node_id}"
    

############################################
class ArbiterTaskNode(ArbiterBaseNode):
    # 만약 지정된 gateway가 없다면, 모든 gateway에 등록
    gateway: str = Field(default='')
    queue: str = Field(default='')
    transformed_parameters: str = Field(default='')
    transformed_return_type: str = Field(default='')
    timeout: int = Field(default=5)

    # for http task
    http: bool = Field(default=False)
    stream: bool = Field(default=False)
    file: bool = Field(default=False)
    request: bool = Field(default=False)
            
    def __eq__(self, other: ArbiterTaskNode) -> bool:
        return (
            self.queue == other.queue
        ) and (
            self.transformed_parameters == other.transformed_parameters
        ) and (
            self.transformed_return_type == other.transformed_return_type
        ) and (
            self.timeout == other.timeout
        ) and (
            self.http == other.http
        ) and (
            self.stream == other.stream
        ) and (
            self.file == other.file
        ) and (
            self.request == other.request
        )

