import uuid
import asyncio
from abc import ABCMeta, abstractmethod
from arbiter.api.stream.data import StreamMessage


class AbstractService(metaclass=ABCMeta):

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def consume_message(self, message: StreamMessage):
        pass

    @abstractmethod
    def produce_message(self, message: StreamMessage):
        pass
