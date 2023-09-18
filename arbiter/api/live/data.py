import asyncio
from typing import Any
from fastapi import WebSocket
from dataclasses import dataclass
from arbiter.api.live.const import LiveConnectionState, LiveSystemEvent


@dataclass
class LiveConnection:
    websocket: WebSocket
    # websocket state is not enough some case
    state: LiveConnectionState = LiveConnectionState.ACTIVATE


@dataclass
class LiveMessage:
    target: str
    data: bytes
    src: str = None
    systemEvent: LiveSystemEvent = None

@dataclass
class LiveUser:
    user_id: str
    message_count: int = 0

class LiveAdapter:
    async def adapt(self, message: Any):
        await asyncio.sleep(1)
        return message