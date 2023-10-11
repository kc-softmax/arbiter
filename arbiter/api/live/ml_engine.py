from __future__ import annotations

import gymnasium as gym

from arbiter.api.live.data import LiveMessage
from arbiter.api.live.engine import LiveAsyncEngine, Adapter
from gymnasium.envs.registration import register, registry


class MARWILTorchAdapter(Adapter):
    
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
    
    # engine의 상위에서 env를 등록하는 과정을 거친다. 사용자가 호출해서 있다면 정상동작하고 없으면 에러를 낸다.
    # env를 직접적으로 호출하는 것을 피한다
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(kwargs.get('frame_rate'))
        self.env: gym.Env = gym.make(kwargs.get('env_id'))
        self.obs, _ = self.env.reset()        

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

    def setup_user(self, user_id: str, user_name: str = None):
        # need add agent to env
        # self.adapter_map[user_id] = MARWILTorchAdapter()
        return super().setup_user(user_id, user_name)
    
    def remove_user(self, user_id: str, user_name: str = None):
        # remove too
        return super().remove_user(user_id, user_name)

    async def pre_processing(self, messages: list[LiveMessage]):
        for message in messages:
            user_id = message.src
            # env의 obs에 agent가 add되었는지 체크해야한다(유저가 들어왔을 때 run이 실행되고있는 타이밍이 안맞을 수 있다
            # 동시에 시작하는 게임이라면 고려할 필요가 없다(env에 이미 유저가 존재한다)
            if user_id in self.adapter_map and user_id in self.obs:
                adapter = self.adapter_map[user_id]
                adapted_action = await adapter.adapt(self.obs[user_id])
                # change message directly
                message.data = adapted_action                
    
    # async def post_processing(self, turn_messages: dict[str, list[any]]):
    #     # run에서 다시 turn_messages를 할당하기 때문에 필요가 없지만, 나중에 무엇이 필요할지 생각해봐야겠다.
    #     turn_messages.clear()
    
    # async def processing(self, turn_messages: dict[str, list[any]]):
    #     # obs는 agent가 사용하고 infos를 client에 보낸다
    #     self.obs, self.rewards, self.terminateds, self.truncateds, self.infos = self.env.step(turn_messages)
    #     live_message = LiveMessage(
    #         src='server',
    #         target=None,
    #         data=base64.urlsafe_b64encode(json.dumps(self.infos).encode()),
    #         systemEvent=None
    #     )
    #     await self._emit_queue.put(live_message)