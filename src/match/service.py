from .adapter import Adapter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketState
from starlette.concurrency import run_until_first_complete
from classic_snake_env.agents.agent import Snake
import logging
from typing import Dict, List, DefaultDict, Any
from collections import defaultdict
log = logging.getLogger(__name__)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
)


class Room:
    
    # adapter와 플레이어 수를 관리한다
    def __init__(self):
        self.adapter: Dict[str, Adapter] = {}
        self.number_of_player: Dict[str, int] = defaultdict(int)
    
    def attach_adapter(self, room_id: str, adapter: Adapter) -> None:
        self.adapter[room_id] = adapter
        
    def detach_adapter(self, room_id: str) -> None:
        self.adapter.pop(room_id)
    
    def join_room(self, room_id: str, user_name: str, websocket: WebSocket) -> None:
        # 유저가 접속하면 snake 객체를 adapter에 추가한다
        self.number_of_player[room_id] += 1
        snake: Snake = Snake(user_name, user_name, (0, 0, 0), False)
        self.adapter[room_id].clients[user_name] = websocket
        self.adapter[room_id].add_player(snake)
    
    def leave_room(self, room_id: str) -> None:
        self.number_of_player[room_id] -= 1
        initialize_adapter: Dict[str, bool] = {}
        for agent_id, client in self.adapter[room_id].clients.items():
            initialize_adapter[agent_id] = client.client_state == WebSocketState.DISCONNECTED
        if all(initialize_adapter.values()): self.detach_adapter(room_id)
