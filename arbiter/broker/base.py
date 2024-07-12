from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncGenerator

"""
잠시 구현을 위해 따로 만들어둔다.
다 만든다음 추상화를 해보자
"""


class MessageBrokerInterface(ABC):

    @abstractmethod
    async def connect(self):
        raise NotImplementedError

    @abstractmethod
    async def disconnect(self):
        raise NotImplementedError

    @abstractmethod
    async def subscribe(self, channel: str):
        raise NotImplementedError

    @abstractmethod
    async def broadcast(self, channel: str, message: bytes):
        raise NotImplementedError

    @abstractmethod
    async def send_message(
        self,
        target: str,
        raw_message: str | bytes,
        timeout: int,
    ):
        raise NotImplementedError

    @abstractmethod
    async def async_send_message(
        self,
        target: str,
        raw_message: str | bytes,
    ):
        raise NotImplementedError

    @abstractmethod
    async def push_message(self, target: str, message: bytes):
        raise NotImplementedError

    @abstractmethod
    async def delete_message(self, message_id: str):
        raise NotImplementedError

    @abstractmethod
    def listen(self, channel: str) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError

    @abstractmethod
    async def periodic_listen(
        self,
        queue: str,
        period: float = 1
    ) -> AsyncGenerator[list[bytes], None]:
        raise NotImplementedError
