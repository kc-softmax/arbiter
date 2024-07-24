from typing import Any, Protocol
from pydantic import BaseModel
from arbiter.constants.enums import (
    StreamCommunicationType,
    StreamMethod, 
    HttpMethod
)


class TaskProtocol(Protocol):
    is_task_function: bool
    task_name: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class StreamTaskProtocol(TaskProtocol):
    routing: bool
    connection: StreamMethod
    communication_type: StreamCommunicationType
    num_of_channels: int

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class HttpTaskProtocol(TaskProtocol):
    routing: bool
    method: HttpMethod
    response_model: BaseModel

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class PeriodicTaskProtocol(TaskProtocol):
    period: float
    queue: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class SubscribeTaskProtocol(TaskProtocol):
    channel: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...
