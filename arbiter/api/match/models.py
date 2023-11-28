from enum import Enum
from sqlmodel import Column, Field, String, Integer, Relationship

from arbiter.api.models import PKModel, BaseSQLModel, TimestampModel


class UserState(str, Enum):
    JOIN = "join"
    LEFT = "left"


class GameRoomsBase(BaseSQLModel):
    game_id: str = Field(sa_column=Column(String(128), unique=True))
    max_player: int | None = Field(sa_column=Column(Integer))


class GameAccessBase(BaseSQLModel):
    # game_rooms와 관계
    user_id: str = Field(sa_column=Column(String(128)))
    user_state: UserState = Field(sa_column=String(25), default=UserState.JOIN)


class GameRooms(PKModel, GameRoomsBase, TimestampModel, table=True):
    __tablename__ = "game_rooms"


class GameAccess(PKModel, GameAccessBase, TimestampModel, table=True):
    __tablename__ = "game_access"
    game_rooms_id: int = Field(foreign_key="game_rooms.id", index=True)
