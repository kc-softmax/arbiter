from __future__ import annotations
import uuid
from typing import Type
from pydantic import BaseModel, Field
from arbiter.constants.enums import ArbiterMessageType, StreamCommand
    
class ArbiterMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    sender_id: str = Field(default=None)
    data: str | bytes = Field(default=None)
    response: bool = Field(default=True)

class ArbiterBroadcastMessage(BaseModel):
    type: ArbiterMessageType

class ArbiterStreamMessage(BaseModel):
    command: StreamCommand
    data: str | bytes = Field(default="")
