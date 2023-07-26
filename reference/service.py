from starlette.websockets import WebSocket, WebSocketState
from typing import Dict
from collections import defaultdict

from server.adapter import Adapter


class Room:
    
    # adapter와 플레이어 수를 관리한다
    def __init__(self):
        self.adapters: Dict[str, Adapter] = {}
        self.number_of_player: Dict[str, int] = defaultdict(int)
        self.clients: Dict[str, Dict[str, WebSocket]] = {}
        self.maximum_players: int = 4
        self.game_state: Dict[str, bool] = {}
        self.history: list[dict[str | int, str]] = []
    
    def attach_adapter(self, room_id: str, adapter: Adapter) -> None:
        self.adapters[room_id] = adapter
        self.game_state[room_id] = False
        
    def detach_adapter(self, room_id: str) -> None:
        self.adapters.pop(room_id)
    
    def join_room(self,
        room_id: str,
        user_name: str,
        user: object,
        websocket: WebSocket
    ) -> bool:
        # 유저가 접속하면 snake 객체를 adapter에 추가한다
        if self.number_of_player[room_id] == self.maximum_players:
            return False
        
        self.number_of_player[room_id] += 1
        self.adapters[room_id].env.add_user(user)
        if self.clients.get(room_id):
            self.clients[room_id][user_name] = websocket
        else:
            self.clients[room_id] = {user_name: websocket}
        return True
    
    def leave_room(self, room_id: str) -> None:
        self.number_of_player[room_id] -= 1
        initialize_adapter: Dict[str, bool] = {}
        for agent_id, client in self.clients[room_id].items():
            initialize_adapter[agent_id] = client.client_state == WebSocketState.DISCONNECTED
        if all(initialize_adapter.values()): self.detach_adapter(room_id)
    
    async def chat_history(self, room_id: str, user_id: str | int, message: str) -> None:
        processing = self.adapters[room_id].execute(user_id, message)
        self.history.append(
            {
                'sender': user_id,
                'message': processing
            }
        )
        for _, client in self.clients[room_id].items():
            await client.send_text(processing)
        