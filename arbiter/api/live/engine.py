from __future__ import annotations

import asyncio
import collections
from typing import Any, Callable, Coroutine
from contextlib import asynccontextmanager
from live.data import LiveMessage, LiveSystemEvent, LiveUser
from live.engine import LiveEngine

class Adapter:
    
    async def adapt(self, message: Any):
        await asyncio.sleep(1)
        return message

class LiveEngine:

    def __init__(self, frame_rate: int = 30):
        # self._waiters: set[asyncio.Future] = set() ?
        
        self.adapter_map: dict[str, Adapter] = collections.defaultdict()
        
        self._publish_queue: asyncio.Queue = asyncio.Queue()
        self._subscribe_queue: collections.deque[LiveMessage] = collections.deque()

    def setup_adapter(self, user_id: str):
        self.adapter_map[user_id] = Adapter()
        
    async def on(self, message: LiveMessage):
        # apply adapter ?
        if message.src in self.adapter_map:
            adapted_message =  await self.adapter_map[message.src].adapt(message)
            self._subscribe_queue.append(adapted_message)
        else:
            self._subscribe_queue.append(message)

    def pre_processing(self) -> LiveMessage:
        pass

    def post_processing(self) -> LiveMessage:
        pass

    def processing(self) -> LiveMessage:
        # message를 모아서 처리한다.
        processed_messages: list[LiveMessage] = []
        while self._subscribe_queue:
            message = self._subscribe_queue.pop()
            processed_messages.append(message)        
        return processed_messages
    
    def reset(self):
        pass

    @asynccontextmanager
    async def subscribe(self) -> LiveEngine:
        try:
            yield self
        finally:
            # finally check before release engine
            pass

    async def __aiter__(self):
        try:
            while True:
                #
                yield await self.get()
        except Exception:
            pass

    async def get(self) -> LiveMessage:  # TOO
        item = await self._queue.get()
        if item is None:
            raise Exception()
        return item
