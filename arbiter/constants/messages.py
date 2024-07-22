from __future__ import annotations
import uuid
from typing import Type, Optional
from pydantic import BaseModel, Field
from arbiter.constants.enums import ArbiterMessageType, StreamCommand
    
class ArbiterMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    sender_id: str = Field(default='')
    data: str | bytes = Field(default='')
    response: bool = Field(default=True)

class ArbiterBroadcastMessage(BaseModel):
    type: ArbiterMessageType
    data: str | bytes = Field(default='')

class ArbiterStreamMessage(BaseModel):
    command: Optional[StreamCommand] = Field(default=None)
    data: str | bytes = Field(default="")
