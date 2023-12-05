import asyncio
import timeit
import collections

from asyncio import Task
from arbiter.api.live.data import LiveMessage
from arbiter.api.live.engine import Adapter, LiveEngine


# create room schema
class LiveRoom:
    def __init__(self, engine: LiveEngine, frame_rate: int = 30):
        self.engine = engine
        self.frame_rate = frame_rate
        self.terminate = False
        self._listen_queue: asyncio.Queue = asyncio.Queue()
        self.emit_task: Task = asyncio.create_task(self.emit())

    def set_room_id(self, room_id: str):
        self.room_id = room_id

    async def setup_user(self, user_id: str, user_name: str = None):
        pass

    async def remove_user(self, user_id: str, user_name: str = None):
        pass

    def publish_to_engine(self, live_message: LiveMessage):
        self.engine._emit_queue.put_nowait(live_message)

    async def on(self, message: LiveMessage):
        self._listen_queue.put_nowait(message)

    async def processing(self, live_message: list[LiveMessage]):
        NotImplementedError()

    async def emit(self):
        time_interval = 1 / self.frame_rate
        waiting_time = time_interval
        turn_messages: collections.deque = collections.deque()
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
