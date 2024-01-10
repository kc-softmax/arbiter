from __future__ import annotations
import asyncio

from contextlib import asynccontextmanager
from typing import AsyncIterator
from arbiter.api.live.data import LiveMessage


class ArbiterContext:
    
    def __init__(self):
        self._emit_queue: asyncio.Queue = asyncio.Queue()

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[ArbiterContext]:
        try:
            yield self
        finally:
            # finally check before release engine
            pass

    async def __aiter__(self) -> AsyncIterator[LiveMessage]:
        try:
            while True:
                yield await self.get()
        except Exception:
            pass

    async def get(self) -> LiveMessage:
        item = await self._emit_queue.get()
        if item is None:
            raise Exception()
        return item
