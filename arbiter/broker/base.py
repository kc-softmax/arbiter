from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Tuple

# 메시지 브로커 클라이언트 인터페이스
class MessageBrokerInterface(ABC):
    def __init__(self) -> None:
        super().__init__()
        self.producer = None
        self.consumer = None

    @abstractmethod
    async def connect(self):
        raise NotImplementedError
    
    @abstractmethod
    async def disconnect(self):
        raise NotImplementedError
    
    @abstractmethod
    async def generate(self) -> Tuple[MessageBrokerInterface, MessageProducerInterface, MessageConsumerInterface]:
        raise NotImplementedError
    
    async def __aenter__(self) -> Tuple[MessageBrokerInterface, MessageProducerInterface, MessageConsumerInterface]:
        await self.connect()
        await self.generate()
        await self.producer.__aenter__()
        await self.consumer.__aenter__()
        return self, self.producer, self.consumer

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.producer.__aexit__(exc_type, exc_value, traceback)
        await self.consumer.__aexit__(exc_type, exc_value, traceback)
        await self.disconnect()

# Producer 인터페이스
class MessageProducerInterface(ABC):

    @abstractmethod
    async def send(self, topic: str, message: Any):
        raise NotImplementedError
    
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

# Consumer 인터페이스
class MessageConsumerInterface(ABC):

    @abstractmethod
    async def subscribe(self, topic: str):
        raise NotImplementedError

    @abstractmethod
    def listen(self) -> AsyncGenerator[Any, None]:
        raise NotImplementedError
    
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass