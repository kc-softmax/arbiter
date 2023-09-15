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
        
        self.user_map: dict[str, LiveUser] = collections.defaultdict()
        self.adapter_map: dict[str, Adapter] = collections.defaultdict()
        
        self._frame_rate: int = frame_rate
        self._publish_queue: asyncio.Queue = asyncio.Queue()
        self._subscribe_queue: collections.deque[LiveMessage] = collections.deque()

    def init_user(self, user_id: str):
        if user_id in self.user_map:
            # TODO export error function
            # TODO example error code
            self._subscribe_queue.append(
                LiveMessage(user_id, 404, LiveSystemEvent.ERROR))
        self.user_map[user_id] = user_id
        # add adapter ?
        self.adapter_map[user_id] = Adapter()

    async def on(self, message: LiveMessage):
        # apply adapter ?
        if message.src in self.adapter_map:
            adapted_message =  await self.adapter_map[message.src].adapt(message)
            self._subscribe_queue.append(adapted_message)
        else:
            self._subscribe_queue.append(message)

    def process_messages(self) -> LiveMessage:
        # message를 모아서 처리한다.
        processed_messages: list[LiveMessage] = []
        while self._subscribe_queue:
            message = self._subscribe_queue.pop()
            # handle message ?
            
            # check message ?
            processed_messages.append(message)
        
        return processed_messages
            
        
    def run(self):
        time_interval = 1 / self._frame_rate
        while (True):
            asyncio.sleep(time_interval)
            results = self.process_messages()
            for result in results:
                self._publish_queue.put_nowait(result)

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
