import uuid
from typing import Any, Type, TypeVar, Generic
from collections import deque

from arbiter.api.live.legacy.adapter import AsyncAdapter


class LiveRoomConfig:

    def __init__(
            self,
            max_users: int,
            adapter_class: Type[AsyncAdapter],
            adapter_model_path: str
    ) -> None:
        self.max_users = max_users
        self.adapter_class = adapter_class
        self.adapter_model_path = adapter_model_path


class BaseLiveRoom:

    def __init__(self, room_id: str, max_users: int | None, adapter: Any) -> None:
        self.room_id = room_id
        self.max_users = max_users if max_users else 10
        self.adapter = adapter
        self.current_users: deque[str] = []

    def is_available(self) -> bool:
        return len(self.current_users) < self.max_users

    def is_empty(self) -> bool:
        return len(self.current_users) == 0

    def join(self, user_id: str):
        self.current_users.append(user_id)

    def leave(self, user_id: str):
        self.current_users.remove(user_id)


# TODO with 매치메이커
RoomType = TypeVar('RoomType', bound=BaseLiveRoom)


class RoomManager(Generic[RoomType]):
    def __init__(self, room_class: Type[RoomType], room_config: LiveRoomConfig) -> None:
        self.room_class = room_class
        self.room_config = room_config
        self.rooms: list[RoomType] = []

    def find_available_room(self) -> RoomType | None:
        available_rooms = [room for room in self.rooms if room.is_available()]
        return available_rooms[0] if available_rooms else None

    def add_room(self, new_room: RoomType):
        self.rooms.append(new_room)

    def create_room(self, room_id: str | None) -> RoomType:
        new_room_id = room_id if room_id != None else str(uuid.uuid4())
        new_room = self.room_class(
            new_room_id,
            self.room_config.max_users,
            self.room_config.adapter_class(self.room_config.adapter_model_path)
        )
        self.rooms.append(new_room)
        return new_room

    async def remove_room(self, room: RoomType):
        self.rooms.remove(room)

    def get_room(self, room_id: str) -> RoomType:
        filtered = [room for room in self.rooms if room.room_id == room_id]
        room = filtered[0] if len(filtered) != 0 else None
        return room
