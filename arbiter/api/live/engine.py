from __future__ import annotations
import asyncio
import collections
import timeit
import gymnasium as gym
import json
import base64
import numpy as np

from asyncio.tasks import Task
from contextlib import asynccontextmanager
from arbiter.api.live.data import LiveMessage
from gymnasium.envs.registration import register, registry
from ray.rllib.policy.policy import Policy
from ray.rllib.algorithms.marwil.marwil_torch_policy import MARWILTorchPolicy
from ray.train import Checkpoint


class Adapter:
    def __init__(self, path: str = 's3://arbiter-server/BC/checkpoint_010000/'):
        check_point = Checkpoint(path)
        self.trainer: dict[str, MARWILTorchPolicy] = Policy.from_checkpoint(check_point)

    async def adapt(self, obs: np.ndarray):
        prediction: tuple = self.trainer['policy_1'].compute_single_action(obs)
        action = prediction[0]
        return [action]

class LiveEngine:

    def __init__(self):
        
        self.adapter_map: dict[str, Adapter] = collections.defaultdict()
        
        self._emit_queue: asyncio.Queue = asyncio.Queue()

    async def setup_user(self, user_id: str, user_name: str=None):
        raise NotImplementedError()
        
    async def remove_user(self, user_id: str, user_name: str=None):
        raise NotImplementedError()
        
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
        # # not override, change behavior
        # if message.src in self.adapter_map:
        #     adapted_message = await self.adapter_map[message.src].adapt(message)
        #     self._listen_queue.put_nowait(adapted_message)
        # else:
        self._listen_queue.put_nowait(message)

    async def pre_processing(self, messages: list[LiveMessage]):
        NotImplementedError()
    
    async def post_processing(self, ):
        NotImplementedError()
    
    async def processing(self, turn_messages: dict[str, list[any]]):
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
                await self.pre_processing(turn_messages)
                await self.processing(turn_messages)
                await self.post_processing(turn_messages)
            except Exception as e:
                print(e)
            elapsed_time = timeit.default_timer() - turn_start_time
            waiting_time = time_interval - elapsed_time
        print('emit task end')
        await self._emit_queue.put_nowait(None)
