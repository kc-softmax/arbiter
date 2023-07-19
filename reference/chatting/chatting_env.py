import gymnasium as gym

from reference.chatting.chat_user import ChatUser


class ChattingEnv(gym.Env):
    def __init__(self, chat_users: list[ChatUser] = [], model: any = None) -> None:
        self.chat_users: dict[str | int, ChatUser] = {
            chat_user.username: chat_user 
            for chat_user in chat_users
        }
        self.model = model
    
    def add_user(self, chat_user: ChatUser) -> None:
        self.chat_users[chat_user.username] = chat_user
    
    def render(self) -> None:
        pass
    
    def _get_dones(self) -> dict[str | int, bool]:
        dones = {
            username: self.chat_users[username].is_leave
            for username in self.chat_users
        }
        if not dones:
            dones['__all__'] = False
        else:
            dones['__all__'] = all(dones.values())
        return dones
    
    def _get_rewards(self) -> dict[str | int, float]:
        pass
    
    def _get_obs(self) -> dict[str | int, str]:
        pass
    
    def _get_infos(self) -> dict[str | int, any]:
        pass
    
    def _get_truncateds(self) -> dict[str | int, bool]:
        truncateds = {
            username: self.chat_users[username].is_leave
            for username in self.chat_users
        }
        if not truncateds:
            truncateds['__all__'] = False
        else:
            truncateds['__all__'] = all(truncateds.values())
        return truncateds
    
    def step(self, actions: dict[str | int, str]
    ) -> tuple[
        dict[str | int, str],
        dict[str | int, float],
        dict[str | int, bool],
        dict[str | int, bool],
        dict[str | int, any]
    ]:
        obs = self._get_obs()
        rewards = self._get_rewards()
        terminateds = self._get_dones()
        truncateds = self._get_truncateds()
        infos = self._get_infos()
        # return obs, rewards, terminateds, truncateds, infos
        return actions, rewards, terminateds, truncateds, infos
