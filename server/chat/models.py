from enum import StrEnum
from server.utils import SchemaMeta
from sqlmodel import Column, Field, SQLModel, String
from datetime import datetime


class ChatRoomType(StrEnum):
    PUBLIC = "public"
    DIRECT = "direct"


# 다른 이모지도 추가 될수 있다고 생각하고 구현해보자
class ChatReactionType(StrEnum):
    Like = "like"
    DISLIKE = "dislike"

# 방 기본 설정
# class ChatRoomConfig:
#     MAX_USERS = 100


# TODO 가장 상위 공통 모델들로 빼기
class BaseSQLModel(SQLModel, metaclass=SchemaMeta):
    deprecated: bool = False


class PKModel(SQLModel):
    id: int | None = Field(default=None, primary_key=True)


class TimestampModel(SQLModel):
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )
    deprecated_at: datetime | None = Field(
        nullable=True
    )


# chat_room.room_id chat_room_user.room_id Join
# room_id를 유지 시키려다가 설계 실수함, room_name을 따로 만들었어야 했음.
class ChatRoomBase(BaseSQLModel, TimestampModel):
    room_id: str | None = Field(sa_column=Column(String(128), unique=True))
    room_name: str = Field(sa_column=Column(String(128)))
    max_users: int = 100
    notice: str | None = Field(sa_column=Column(String(128), default=""))
    type: str | None = Field(sa_column=Column(String(128), default=ChatRoomType.PUBLIC))


class ChatRoom(PKModel, ChatRoomBase, table=True):
    __tablename__ = "chat_room"


class ChatRoomUserBase(BaseSQLModel, TimestampModel):
    is_connected: bool = True
    # TODO: 삭제
    message: str | None = Field(sa_column=Column(String(128)))
    user_id: int = Field(default=None)
    room_id: str = Field(sa_column=Column(String(128)))


class ChatRoomUser(PKModel, ChatRoomUserBase, table=True):
    __tablename__ = "chat_room_user"


# TODO: 삭제
class ChatBase(BaseSQLModel, TimestampModel):
    user_id: int = Field(sa_column=Column(String(128)))
    user_name: int | None = Field(sa_column=Column(String(128)))
    room_id: str = Field(sa_column=Column(String(128)))
    message: str | None = Field(sa_column=Column(String(128)))

# TODO: 삭제
class Chat(PKModel, ChatBase, table=True):
    __tablename__ = "chat"

# TODO: 삭제
class ChatReactionBase(BaseSQLModel, TimestampModel):
    message_id: int
    user_id: int
    type: str = Field(sa_column=Column(String(128)))

# TODO: 삭제
class ChatReaction(PKModel, ChatReactionBase, table=True):
    __tablename__ = "current_user"
