import uuid
import asyncio
from abc import ABC, abstractmethod
from arbiter.api.stream.data import StreamMessage
from arbiter.broker.base import MessageConsumerInterface, MessageProducerInterface


class AbstractService(ABC):

    def __init__(
        self,
        producer: MessageProducerInterface,
        consumer: MessageConsumerInterface,
    ):
        self.service_id = uuid.uuid4()
        self.producer = producer
        self.consumer = consumer
        self.task: asyncio.Task = None

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def consuming_message(self, message: StreamMessage):
        pass

    @abstractmethod
    async def producing(self):
        pass

    async def consume(self):
        async for message in self.consumer.listen():
            self.consuming_message(message)
            print(f"message: {message}")

    async def __aenter__(self):
        # self.task = asyncio.create_task(self.consume())
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()
        await self.task
