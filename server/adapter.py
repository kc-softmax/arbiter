import asyncio
import timeit
import gymnasium as gym
from typing import Dict, Any
from collections import deque
from contextlib import asynccontextmanager


class Adapter:
    def add_user_message(self) -> None:
        raise NotImplementedError()

    def execute(self) -> None | Dict[str | int, Any]:
        raise NotImplementedError()


class GymAdapter(Adapter):
    def __init__(self, env: gym.Env) -> None:
        self.env: gym.Env = env
        self.message: asyncio.Queue = asyncio.Queue()
        self.actions: deque = deque()

    def add_user_message(self, agent_id: int | str, action: int) -> None:
        # action은 미리 env에서 정의한 gym.spaces.Discrete의 범위내 값이다.
        self.actions.append((agent_id, action))

    async def execute(self) -> None:
        waiting_time: float = 0.1
        loop_per_sec: float = 0.1
        terminateds: bool = False
        # multiagent일 경우에 dict으로 처리해야한다
        # 모든 유저가 죽었을 경우에도 terminated가 True가 되어 종료된다.
        while not terminateds:
            # 약 1초에 10번 처리한다.
            await asyncio.sleep(waiting_time)
            turn_start_time: float = timeit.default_timer()
            actions: Dict[str | int, int] = {
                agent_id: action
                for agent_id, action in self.actions
            }
            # env의 step에서 action에 대한 타입 체크를 해야한다.
            # multiagent일 경우 step에서 dict으로 처리해야한다.
            obs, rewards, terminateds, truncateds, infos = self.env.step(actions)
            # TODO: multiagent의 경우를 생각해야한다.
            if type(terminateds) == dict:
                terminateds = all(terminateds.values())
            # step의 결과인 update된 state를 queue에 넣는다.
            await self.message.put(obs)
            elapsed_time = timeit.default_timer() - turn_start_time
            waiting_time = loop_per_sec - elapsed_time
            waiting_time = 0 if waiting_time < 0 else waiting_time
            # 이전에 남은 action이 영향을 주면 안되기 때문에 clear한다.
            self.actions.clear()


class ChatAdapter(Adapter):
    """
        ChatAdapter for multiplay chatting
    """

    def __init__(self, model: any) -> None:
        # 처음에는 단순하게 비속어가 담긴 문장
        self.model: any = model
        self.client_message: deque = deque()
        self.broadcast_message: asyncio.Queue = asyncio.Queue()

    def add_user_message(self) -> None:
        pass

    def execute(self, user_id: int | str, message: str) -> dict[str, int | str]:
        # 처음에는 단순하게 '비속어'라는 단어의 유무에 따라 유저의 메시지를 분류한다.
        is_bad_comments: bool = False
        if '비속어' in message:
            is_bad_comments = True

        # return되는 값은 변경될 수 있습니다.
        user_message: dict[str | int, str] = {
            'user_id': user_id,
            'message': message,
            'is_bad_comments': is_bad_comments
        }
        return user_message
