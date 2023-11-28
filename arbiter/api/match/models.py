from enum import Enum
from sqlmodel import Column, Field, String, Integer, Relationship

from arbiter.api.models import PKModel, BaseSQLModel, TimestampModel


class GameState(str, Enum):
    AVAILABLE = "available"
    FULL = "full"


class UserState(str, Enum):
    JOIN = "join"
    LEFT = "left"


# auth 도메인 모델들
class GameRoomsBase(BaseSQLModel):
    game_id: str = Field(sa_column=Column(String(128), unique=True))
    max_players: int | None = Field(sa_column=Column(Integer))
    now_players: int | None = Field(sa_column=Integer, default=0)
    game_state: GameState = Field(sa_column=String(25), default=GameState.AVAILABLE)


class GameAccessBase(BaseSQLModel):
    # game_rooms와 관계
    user_id: str = Field(sa_column=Column(String(128)))
    user_state: GameState = Field(sa_column=String(25), default=UserState.JOIN)


class GameRooms(PKModel, GameRoomsBase, TimestampModel, table=True):
    __tablename__ = "game_rooms"


class GameAccess(PKModel, GameAccessBase, TimestampModel, table=True):
    __tablename__ = "game_access"
    game_rooms_id: int = Field(foreign_key="game_rooms.id", index=True)
