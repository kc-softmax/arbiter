from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
from typing import AsyncGenerator, Any

class ArbiterBrokerInterface(ABC):
    
    def __init__(
        self,
        *,
        name: str,
        log_level: str = "info",
        log_format: str = "[arbiter] - %(level)s - %(message)s - %(datetime)s",
    ) -> None:
        super().__init__()
        self.name = name
        self.log_level = log_level
        self.log_format = log_format

    @abstractmethod
    async def connect(self):
        raise NotImplementedError
    
    @abstractmethod
    async def disconnect(self):
        raise NotImplementedError
    
    @abstractmethod
    async def request(
        self,
        target: str,
        message: bytes,
        timeout: int
    ) -> Any:
        raise NotImplementedError
    
    @abstractmethod
    async def stream(
        self,
        target: str, 
        message: bytes,
        timeout: int
    ) -> AsyncGenerator[Any, None]:        
        raise NotImplementedError
    
    @abstractmethod
    async def emit(
        self, 
        target: str,
        message: bytes,
        reply: str = ''
    ):
        raise NotImplementedError
    
    @abstractmethod
    async def broadcast(
        self, 
        target: str,
        message: bytes,
        reply: str = '',
    ):
        raise NotImplementedError

    @abstractmethod
    async def listen(
        self,
        queue: str,
        timeout: int = 0
    ) -> AsyncGenerator[
        bytes,
        None
    ]:
        raise NotImplementedError

    @abstractmethod
    async def subscribe_listen(
        self,
        queue: str,
    ) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError

    @abstractmethod
    async def periodic_listen(
        self,
        queue: str,
        interval: float = 1
    ) -> AsyncGenerator[list[bytes], None]:
        raise NotImplementedError