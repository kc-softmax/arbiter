from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Type, Union
from arbiter.constants import ArbiterMessage


"""
잠시 구현을 위해 따로 만들어둔다.
다 만든다음 추상화를 해보자
"""


class ArbiterInterface(ABC):

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
        receiver_id: str,
        message: ArbiterMessage,
        timeout: float
    ):
        raise NotImplementedError

    @abstractmethod
    async def push_message(self, target: str, message: bytes):
        raise NotImplementedError

    @abstractmethod
    async def delete_message(self, message_id: str):
        raise NotImplementedError

    @abstractmethod
    def listen(self, channel: str, timeout: int) -> AsyncGenerator[ArbiterMessage, None]:
        raise NotImplementedError

    @abstractmethod
    async def listen_bytes(self, channel: str, timeout: int = 0) -> AsyncGenerator[
        bytes,
        None
    ]:
        raise NotImplementedError

    @abstractmethod
    async def periodic_listen(
        self,
        queue: str,
        period: float = 1
    ) -> AsyncGenerator[list[bytes], None]:
        raise NotImplementedError
