from __future__ import annotations
from typing import AsyncGenerator, Tuple, TypeVar, Generic, Protocol

T = TypeVar('T')

# 메시지 브로커 클라이언트 인터페이스
class MessageBrokerInterface(Protocol, Generic[T]):
    client: T
    producer: MessageProducerInterface
    consumer: MessageConsumerInterface

    def __init__(self, client: T) -> None:
        super().__init__()
        self.client =  client

    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError
    
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
class MessageProducerInterface(Generic[T]):
    def __init__(self, client: T):
        self.client = client

    async def send(self, topic: str, message: str):
        raise NotImplementedError
    
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

# Consumer 인터페이스
class MessageConsumerInterface(Generic[T]):
    def __init__(self, client: T):
        self.client = client

    async def subscribe(self, topic: str):
        raise NotImplementedError

    async def listen(self) -> AsyncGenerator[str, None]:
        raise NotImplementedError
    
    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass