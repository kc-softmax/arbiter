import asyncio

from typing import Any
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from dataclasses import dataclass, field
from arbiter.api.live.const import LiveConnectionState, LiveSystemEvent


class LiveAdapter:
    # TODO: labs에서 모델을 가져오게 된다. trainer를 매번 초기화하지 않는 방법을 고려해본다.
    # multiagent로 학습되었기 때문에 사용하는 user별로 자신의 obs를 넘겨주면 된다
    # def __init__(self, path: str = 's3://arbiter-server/BC/checkpoint_010000/'):
    #     labs.get_model()

    async def adapt_in(self, message: Any):
        return message

    async def adapt_out(self, message: Any):
        return message


@dataclass
class LiveConnection:
    websocket: WebSocket
    # websocket state is not enough some case
    state: LiveConnectionState = LiveConnectionState.ACTIVATE
    adapter: LiveAdapter = None
    joined_groups: list[str] = field(default_factory=lambda: [])

    async def send_message(self, message: bytes):
        if self.websocket.client_state == WebSocketState.DISCONNECTED:
            return
        if self.adapter:
            message = await self.adapter.adapt_out(message)
        try: await self.websocket.send_bytes(message)
        except Exception as e: print(e, 'in send_message')

@dataclass
class LiveMessage:
    data: bytes = None
    src: str = None
    target: str = None
    systemEvent: LiveSystemEvent = None

@dataclass
class LiveUser:
    user_id: str
    message_count: int = 0

