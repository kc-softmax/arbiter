import asyncio
from typing import Any
from fastapi import WebSocket
from dataclasses import dataclass
from live.const import LiveConnectionState, LiveSystemEvent


@dataclass
class LiveConnection:
    websocket: WebSocket
    # websocket state is not enough some case
    state: LiveConnectionState = LiveConnectionState.PENDING


@dataclass
class LiveMessage:
    src: str
    target: str
    data: bytes
    systemEvent: LiveSystemEvent = None

@dataclass
class LiveUser:
    user_id: str
    message_count: int = 0

class LiveAdapter:
    async def adapt(self, message: Any):
        await asyncio.sleep(1)
        return message