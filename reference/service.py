from starlette.websockets import WebSocket, WebSocketState
from typing import Dict
from collections import defaultdict

from server.adapter import Adapter

import uuid


class Room:
    
    # adapter와 플레이어 수를 관리한다
    def __init__(self, room_id: uuid.UUID, adapter: Adapter):
        self.adapter: Adapter = adapter
        self.number_of_player: Dict[str, int] = defaultdict(int)
        self.clients: Dict[str, WebSocket] = {}
        self.maximum_players: int = 4
        self.game_state: bool = False
        self.history: list[dict[str | int, str]] = []
    
    def is_available(self) -> bool:
        possible = True
        if len(self.clients) == self.maximum_players:
            possible = False
        return possible

    def join_room(self,
        room_id: str,
        user_name: str,
        user: object,
        websocket: WebSocket
    ) -> bool:
        if self.number_of_player[room_id] == self.maximum_players:
            return False
        
        self.number_of_player[room_id] += 1
        self.adapter.env.add_user(user)
        if self.clients.get(room_id):
            self.clients[room_id][user_name] = websocket
        else:
            self.clients[room_id] = {user_name: websocket}
        return True
    
    def leave_room(self, user_id) -> None:
        self.number_of_player -= 1
        self.clients.pop(user_id)
    
    async def chat_history(self, room_id: str, user_id: str | int, message: str) -> None:
        processing = self.adapter.execute(user_id, message)
        self.history.append(
            {
                'sender': user_id,
                'message': processing
            }
        )
        for _, client in self.clients[room_id].items():
            await client.send_text(processing)


class RoomManager:
    def __init__(self) -> None:
        self.rooms: list[Room] = []

    def find_available_room(self) -> Room | None:
        available_rooms = [room for room in self.rooms if room.is_available()]
        return None if not available_rooms else available_rooms[0]

    def create_room(self, room_id: uuid.UUID, adapter: Adapter) -> Room:
        new_room = Room(room_id, adapter)
        self.rooms.append(new_room)
        return new_room

    def remove_room(self, room: Room):
        self.rooms.remove(room)