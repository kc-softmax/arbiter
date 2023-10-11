import asyncio

from typing import Any
from fastapi import WebSocket
from dataclasses import dataclass

from arbiter.api.live.const import LiveConnectionState, LiveSystemEvent


class LiveAdapter:
    # TODO: labs에서 모델을 가져오게 된다. trainer를 매번 초기화하지 않는 방법을 고려해본다.
    # multiagent로 학습되었기 때문에 사용하는 user별로 자신의 obs를 넘겨주면 된다
    # def __init__(self, path: str = 's3://arbiter-server/BC/checkpoint_010000/'):
    #     labs.get_model()

    async def adapt(self, message: Any):
        await asyncio.sleep(1)
        return message


class MARWILTorchAdapter(LiveAdapter):

    import numpy as np

    def __init__(self, path: str = 's3://arbiter-server/BC/checkpoint_010000/'):
        from ray.rllib.policy.policy import Policy
        from ray.rllib.algorithms.marwil.marwil_torch_policy import MARWILTorchPolicy
        # from ray.train import Checkpoint
        # check_point = Checkpoint(path)
        self.trainer: dict[str, MARWILTorchPolicy] = Policy.from_checkpoint(
            '/Users/jared/github/arbiter-server/arbiter/api/live/checkpoint_010000/')

    async def adapt(self, obs: np.ndarray):
        prediction: tuple = self.trainer['policy_1'].compute_single_action(obs)
        action = prediction[0]
        return [action]


@dataclass
class LiveConnection:
    websocket: WebSocket
    # websocket state is not enough some case
    state: LiveConnectionState = LiveConnectionState.ACTIVATE
    adapter: LiveAdapter = None


@dataclass
class LiveMessage:
    data: bytes = None
    src: str = None
    target: str = None
    systemEvent: LiveSystemEvent = None

@dataclass
class LiveUser:
    user_id: str
    message_count: int = 0

class LiveAdapter:
    async def adapt(self, message: Any):
        await asyncio.sleep(1)
        return message