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

    async def setup_user(self, user_id: str, use_adapter: bool = False):
        if use_adapter: self.adapter_map[user_id] = Adapter()
        
    async def remove_user(self, user_id: str, use_adapter: bool = False):
        if use_adapter: self.adapter_map.pop(user_id)
        
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
            adapted_message = await self.adapter_map[message.src].adapt(message)
            self._emit_queue.put_nowait(adapted_message)
        else:
            self._emit_queue.put_nowait(message)

    async def pre_processing(self, turn_messages: dict[str, list[any]]):
        NotImplementedError()
    
    async def post_processing(self, turn_messages: dict[str, list[any]]):
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


class LiveAsyncEnvEngine(LiveAsyncEngine):
    """LiveAsyncEnvEngine Summary

    Args:
        env_id (str): 사용할 env의 id를 지정한다(gymnasium에서 env 초기화시 사용)
        
        entry_point (str): env의 package 경로를 다음과 같이 입력한다

        ex) from maenv.dusty.dusty_env import DustyEnv
            `maenv.dusty.dusty_env:DustyEnv`
        
        env_config (dict): env를 초기화 할 때 사용할 config를 정의한다
        
        frame_rate (int): 초당 rendering 수를 지정한다
    """
    def __init__(self, *args, **kwargs) -> None:
        self.env: gym.Env = gym.make(kwargs.get('env_id'))
        self.obs, _ = self.env.reset()
        super().__init__(kwargs.get('frame_rate'))

    def __new__(cls, *args, **kwargs) -> LiveAsyncEnvEngine:
        if not kwargs.get('env_id') or not kwargs.get('entry_point'):
            raise AttributeError("Check your env_id and entroy_point field")

        if kwargs['env_id'] not in registry:
            register(
                id=kwargs['env_id'],
                entry_point=kwargs['entry_point'],
                kwargs=kwargs.get('env_config', {})
            )
        return super().__new__(cls)
    
    async def on(self, message: LiveMessage):
        # not override, change behavior
        deserialize = {
            message.src: json.loads(base64.urlsafe_b64decode(message.data))
        }
        self._listen_queue.put_nowait(deserialize)

    async def pre_processing(self, turn_messages: dict[str, list[any]]):
        for agent_id, adapter in self.adapter_map.items():
            # env의 obs에 agent가 add되었는지 체크해야한다(유저가 들어왔을 때 run이 실행되고있는 타이밍이 안맞을 수 있다
            # 동시에 시작하는 게임이라면 고려할 필요가 없다(env에 이미 유저가 존재한다)
            if agent_id in self.env.obs:
                turn_messages[agent_id] = await adapter.adapt(self.env.obs[agent_id])
    
    async def post_processing(self, turn_messages: dict[str, list[any]]):
        # run에서 다시 turn_messages를 할당하기 때문에 필요가 없지만, 나중에 무엇이 필요할지 생각해봐야겠다.
        turn_messages.clear()
    
    async def processing(self, turn_messages: dict[str, list[any]]):
        # obs는 agent가 사용하고 infos를 client에 보낸다
        self.obs, self.rewards, self.terminateds, self.truncateds, self.infos = self.env.step(turn_messages)
        live_message = LiveMessage(
            src='server',
            target=None,
            data=base64.urlsafe_b64encode(json.dumps(self.infos).encode()),
            systemEvent=None
        )
        await self._emit_queue.put(live_message)
        
    async def emit(self):
        time_interval = 1 / self.frame_rate
        waiting_time = time_interval
        # turn_messages = collections.deque()
        while not self.terminate:
            waiting_time > 0 and await asyncio.sleep(waiting_time)
            turn_start_time = timeit.default_timer()
            current_message_count = self._listen_queue.qsize()
            turn_messages = {
                agent_id: [None]
                for agent_id in self.env.agents
            }
            for _ in range(current_message_count):
                turn_messages.update(self._listen_queue.get_nowait())
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
