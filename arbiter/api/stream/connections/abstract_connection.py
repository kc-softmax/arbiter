from abc import ABC, abstractmethod
from fastapi import WebSocket


class ArbiterConnection(ABC):
    # 모든 connection은 처음에 websocket을 기반으로 handshake를 진행한다.

    def __init__(
        self,
        websocket: WebSocket,
    ):
        self.websocket: WebSocket = websocket

    @abstractmethod
    async def run(self):
        """
        Frameworks expecting callback functions of specific signatures 
        might be type hinted using Callable[[Arg1Type, Arg2Type], ReturnType].
        """
        pass

    @abstractmethod
    async def send_message(self, bytes: bytes):
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def error(self, reason: str | None):
        pass
