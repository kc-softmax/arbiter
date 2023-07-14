from classic_snake_env.snake_env import SnakeEnv
from classic_snake_env.const import GameConfig, GameState
from classic_snake_env.agents.agent import Snake
from typing import List, Dict, Any
from starlette.websockets import WebSocket, WebSocketState
import asyncio
import timeit


class Adapter(GameConfig):
    def __init__(self, env: SnakeEnv = SnakeEnv()) -> None:
        self.env = env
        self.game_players: Any = None
        self.game_agents: Any = None
        self._terminate_flag: bool = False
        self.clients: Dict[str, WebSocket] = {}
        self.is_started: bool = False
    
    def add_player(self, player: Snake) -> None:
        self.env.add_snake(player)
    
    def remove_player(self, player: Snake) -> None:
        self.env.remove_snake(player)
    
    async def send_to_client(self, message: Dict[str, List]) -> None:
        for _, websocket in self.clients.items():
            if websocket.client_state == WebSocketState.CONNECTED:
                message['event'] = 'play'
                await websocket.send_json(message)
    
    def kick_client(self) -> None:
        disconnected_clients = []
        for agent_id, websocket in self.clients.items():
            if websocket.client_state != WebSocketState.CONNECTED:
                disconnected_clients.append(agent_id)
        for agent_id in disconnected_clients: self.clients.pop(agent_id)
    
    def update_player_action(self, player_id: str, action: int) -> bool:
        if player_id not in self.env.snakes:
            return False
        player = self.env.snakes[player_id]
        # client 로 부터 action이 들어오면 timer를 초기화 한다
        player.set_action(action)
        return True
    
    async def terminate(self):
        self._terminate_flag = True
    
    async def run(self) -> None:
        waiting_time = 0.1
        loop_per_sec = 1 / GameConfig.fps
        turn_start_time = timeit.default_timer()
        while not self._terminate_flag:
            await asyncio.sleep(waiting_time)
            turn_start_time = timeit.default_timer()
            # broadcast to all users
            actions = {
                player_id: player.get_action()
                for player_id, player in self.env.snakes.items()
                if player.state == GameState.ACTIVE and player.is_alive
            }
            # Agents will use this when reinforcement learning
            obs, rewards, terminated, truncateds, infos = self.env.step(actions)
            messages = {
                player_id: snake.body
                for player_id, snake in self.env.snakes.items() if snake.is_alive
            }
            messages['items'] = self.env.game_items.items
            await self.send_to_client(messages)
            self.kick_client()
            if not self.clients: await self.terminate()
            elapsed_time = timeit.default_timer() - turn_start_time            
            waiting_time = loop_per_sec - elapsed_time 
            waiting_time = 0 if waiting_time < 0 else waiting_time
