from __future__ import annotations
import uuid
from typing import Any
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
    channel: str = Field(default="")
    target: str = Field(default="")
    data: Any = Field(default=None)
