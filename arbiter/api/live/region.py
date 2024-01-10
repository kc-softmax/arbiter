import asyncio
import collections
import timeit

from asyncio import Task
from arbiter.api.live.data import LiveMessage


class Region:
    def __init__(self, frame_rate: int = 30):
        self.frame_rate = frame_rate
        self.terminate = False
        self.max_player = float('inf')
        self.now_player = 0
        self._listen_queue: asyncio.Queue = asyncio.Queue()
        self.emit_task: Task = asyncio.create_task(self.emit())

    async def setup_user(self, user_id: str, user_name: str):
        NotImplementedError()

    async def remove_user(self, user_id: str, user_name: str = None):
        NotImplementedError()

    async def on(self, message: LiveMessage):
        self._listen_queue.put_nowait(message)

    async def processing(self, live_message: dict[str, list[any]]):
        # await self._emit_queue.put(live_message)
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
                await self.processing(turn_messages)
            except Exception as e:
                print(e)
            turn_messages.clear()
            elapsed_time = timeit.default_timer() - turn_start_time
            waiting_time = time_interval - elapsed_time
        print('emit task end')
