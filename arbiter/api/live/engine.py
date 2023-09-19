from __future__ import annotations
import asyncio
import collections
import timeit
from asyncio.tasks import Task
from typing import Any
from contextlib import asynccontextmanager
from arbiter.api.live.data import LiveMessage

class Adapter:
    
    async def adapt(self, message: Any):
        await asyncio.sleep(1)
        return message # action

class LiveEngine:

    def __init__(self):
        
        self.adapter_map: dict[str, Adapter] = collections.defaultdict()
        
        self._emit_queue: asyncio.Queue = asyncio.Queue()

    async def setup_user(self, user_id: str, user_name: str=None):
        pass
        # self.adapter_map[user_id] = Adapter()
        
    async def remove_user(self, user_id: str, user_name: str=None):
        pass
        # self.adapter_map.pop(user_id)
        
    async def on(self, message: LiveMessage):
        # apply adapter ?
        if message.src in self.adapter_map:
            adapted_message = await self.adapter_map[message.src].adapt(message)
            self._emit_queue.put_nowait(adapted_message)
        else:
            self._emit_queue.put_nowait(message)

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
        item = await self._emit_queue.get()
        if item is None:
            raise Exception()
        return item

class LiveAsyncEngine(LiveEngine):

    def __init__(self, frame_rate: int = 30):
        super().__init__()
        self.frame_rate = frame_rate
        self.terminate = False        
        self._listen_queue: asyncio.Queue = asyncio.Queue()
        self.emit_task: Task = asyncio.create_task(self.emit())

        
    async def on(self, message: LiveMessage):
        # not override, change behavior
        if message.src in self.adapter_map:
            adapted_message =  await self.adapter_map[message.src].adapt(message)
            self._listen_queue.put_nowait(adapted_message)
        else:
            self._listen_queue.put_nowait(message)

    async def pre_processing(self):
        NotImplementedError()
    
    async def post_processing(self):
        NotImplementedError()
    
    async def processing(self, messages: list[LiveMessage]):
        # await self._emit_queue.put_nowait(
            # LiveMessage(data='Hello World)
        NotImplementedError()
        
    async def emit(self):
        time_interval = 1 / self.frame_rate
        waiting_time = time_interval
        turn_messages = collections.deque()
        while not self.terminate:
            waiting_time > 0 and await asyncio.sleep(waiting_time)
            turn_start_time = timeit.default_timer()
            current_message_count = self._listen_queue.qsize()
            for _ in range(current_message_count):
                turn_messages.appendleft(self._listen_queue.get_nowait())
            try:
                await self.pre_processing()
                await self.processing(turn_messages)
                await self.post_processing()
            except Exception as e:
                print(e)
            turn_messages.clear()
            elapsed_time = timeit.default_timer() - turn_start_time
            waiting_time = time_interval - elapsed_time
        print('emit task end')
        await self._emit_queue.put_nowait(None)
        