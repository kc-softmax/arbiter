from typing import Any, Protocol
from arbiter.constants.enums import StreamMethod, HttpMethod


class TaskProtocol(Protocol):
    is_task_function: bool

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class StreamTaskProtocol(TaskProtocol):
    auth: bool
    connection: StreamMethod

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class HttpTaskProtocol(TaskProtocol):
    auth: bool
    method: HttpMethod

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class PeriodicTaskProtocol(TaskProtocol):
    period: float

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...


class SubscribeTaskProtocol(TaskProtocol):
    channel: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        ...
