from __future__ import annotations
import uuid
from typing import Optional, Any, Optional
from pydantic import BaseModel, Field

class ArbiterStreamMessage(BaseModel):
    channel: str = Field(default="")
    target: str = Field(default="")
    data: Any = Field(default=None)

class RequestInfo(BaseModel):
    host: str
    port: int
