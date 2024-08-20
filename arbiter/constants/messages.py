from __future__ import annotations
import uuid
from typing import Any, Optional
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

class ConnectionInfo(BaseModel):
    host: str
    port: int

# class RequestData(BaseModel):
#     method: str
#     url: str
#     headers: dict[str, str]
#     query_params: dict[str, str]
#     cookies: dict[str, str]
#     body: Optional[Any]
#     client_host: str
#     test: list[str]