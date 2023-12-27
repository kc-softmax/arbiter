from __future__ import annotations
import asyncio
import collections
import timeit

from typing import AsyncIterator
from asyncio.tasks import Task
from contextlib import asynccontextmanager
from arbiter.api.live.data import LiveMessage
from arbiter.api.auth.dependencies import unit_of_work
from arbiter.api.match.models import UserState, GameAccess
from arbiter.api.match.repository import game_access_repository


class Adapter:
    async def adapt(self, obs: any):
        NotImplementedError()


class LiveEngine:

    adapter_map: dict[str, Adapter] = collections.defaultdict()
    _emit_queue: asyncio.Queue = asyncio.Queue()
    live_rooms: dict[str, LiveRoom] = {}
    # 기존 코드
    # def __init__(self):
    #     self.adapter_map: dict[str, Adapter] = collections.defaultdict()
    #     self._emit_queue: asyncio.Queue = asyncio.Queue()

    # async def setup_user(self, user_id: str, user_name: str = None):
    #     pass

    # async def remove_user(self, user_id: str, user_name: str = None):
    #     pass

    # async def on(self, message: LiveMessage):
    #     # apply adapter ?
    #     if message.src in self.adapter_map:
    #         adapted_message = await self.adapter_map[message.src].adapt(message)
    #         self._emit_queue.put_nowait(adapted_message)
    #     else:
    #         self._emit_queue.put_nowait(message)

    # 변경 코드
    def __init__(self, room_id: str, live_room: LiveRoom):
        self.live_rooms[room_id] = live_room

    async def enter_room(self, room_id: str, user_id: str) -> GameAccess:
        async with unit_of_work.transaction() as session:
            record = await game_access_repository.add(
                session,
                GameAccess(
                    user_id=user_id,
                    game_rooms_id=room_id
                )
            )
            return record

    async def leave_room(self, user: GameAccess):
        async with unit_of_work.transaction() as session:
            user.user_state = UserState.LEFT
            await game_access_repository.update(
                session,
                user
            )

    def release_room(self, room_id: str):
        self.live_rooms[room_id].done_emit()

    async def setup_room_user(self, room_id: str, user_id: str, user_name: str = None):
        await self.live_rooms[room_id].setup_user(user_id, user_name)

    async def remove_user(self, user_id: str, user_name: str = None):
        pass

    async def on_room(self, room_id: str, message: LiveMessage):
        self.live_rooms[room_id].on(message)

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[LiveEngine]:
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
        await self._emit_queue.put_nowait(None)


class LiveRoom(LiveEngine):
    def __init__(self, room_id: str, frame_rate: int = 30):
        super().__init__(room_id, self)
        self.room_id = room_id
        self.frame_rate = frame_rate
        self.terminate = False
        self._listen_queue: asyncio.Queue = asyncio.Queue()
        self.emit_task: Task = asyncio.create_task(self.emit())

    async def setup_user(self, user_id: str, user_name: str = None):
        pass

    async def remove_user(self, user_id: str, user_name: str = None):
        pass

    def publish_to_engine(self, live_message: LiveMessage):
        # live service의 queue
        live_message.target = self.room_id
        self._emit_queue.put_nowait(live_message)

    def on(self, live_message: LiveMessage):
        self._listen_queue.put_nowait(live_message)

    async def processing(self, live_message: list[LiveMessage]):
        NotImplementedError()

    def done_emit(self):
        self.terminate = True
        self.emit_task.cancel()

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
