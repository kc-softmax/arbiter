from starlette.websockets import WebSocket, WebSocketState
from classic_snake_env.agents.agent import Snake
from typing import Dict
from collections import defaultdict

from server.gym_adapter import GymAdapter


class Room:
    
    # adapter와 플레이어 수를 관리한다
    def __init__(self):
        self.adapter: Dict[str, GymAdapter] = {}
        self.number_of_player: Dict[str, int] = defaultdict(int)
        self.clients: Dict[str, Dict[str, WebSocket]] = {}
        self.maximum_players: int = 2
        self.game_state: Dict[str, bool] = {}
    
    def attach_adapter(self, room_id: str, adapter: GymAdapter) -> None:
        self.adapter[room_id] = adapter
        self.game_state[room_id] = False
        
    def detach_adapter(self, room_id: str) -> None:
        self.adapter.pop(room_id)
    
    def join_room(self, room_id: str, user_name: str, websocket: WebSocket) -> None:
        # 유저가 접속하면 snake 객체를 adapter에 추가한다
        self.number_of_player[room_id] += 1
        snake: Snake = Snake(user_name, user_name, (0, 0, 0), False)
        self.adapter[room_id].env.add_snake(snake)
        if self.clients.get(room_id):
            self.clients[room_id][user_name] = websocket
        else:
            self.clients[room_id] = {user_name: websocket}
    
    def leave_room(self, room_id: str) -> None:
        self.number_of_player[room_id] -= 1
        initialize_adapter: Dict[str, bool] = {}
        for agent_id, client in self.clients[room_id].items():
            initialize_adapter[agent_id] = client.client_state == WebSocketState.DISCONNECTED
        if all(initialize_adapter.values()): self.detach_adapter(room_id)
        