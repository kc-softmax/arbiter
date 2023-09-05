from starlette.websockets import WebSocket

from reference.adapter import AsyncAdapter

import uuid
import json


class Room:
    
    # adapter와 플레이어 수를 관리한다
    def __init__(self, room_id: uuid.UUID, adapter: AsyncAdapter):
        self.room_id = room_id
        self.adapter: AsyncAdapter = adapter
        self.number_of_player: int = 0
        self.clients: dict[str, WebSocket] = {}
        self.maximum_players: int = 4
        self.history: list[dict[str | int, str]] = []
    
    def is_available(self) -> bool:
        possible = True
        if len(self.clients) == self.maximum_players:
            possible = False
        return possible

    def join_room(self,
        room_id: str,
        user_id: str,
        websocket: WebSocket
    ) -> bool:
        if self.number_of_player == self.maximum_players:
            return False
        
        self.number_of_player += 1
        if self.clients.get(room_id):
            self.clients[room_id][user_id] = websocket
        else:
            self.clients[room_id] = {user_id: websocket}
        return True
    
    def leave_room(self, user_id: str) -> None:
        self.number_of_player -= 1
        self.clients.pop(user_id)


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}

    def find_available_room(self) -> Room | None:
        available_rooms = [room for room in self.rooms.values() if room.is_available()]
        return available_rooms[0] if available_rooms else None

    def create_room(self, room_id: uuid.UUID, adapter: AsyncAdapter) -> Room:
        new_room = Room(room_id, adapter)
        self.rooms[room_id] = new_room
        return new_room

    def remove_room(self, room_id: str):
        self.rooms.pop(room_id)
