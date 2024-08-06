from __future__ import annotations
import uuid
from typing import Any
from pydantic import BaseModel, Field
from arbiter.constants.enums import ArbiterDataType, StreamCommand
    
class ArbiterMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    data: str | bytes = Field(default='')

class ArbiterTypedData(BaseModel):
    type: ArbiterDataType
    data: str | bytes = Field(default='')

class ArbiterStreamMessage(BaseModel):
    channel: str = Field(default="")
    target: str = Field(default="")
    data: Any = Field(default=None)
