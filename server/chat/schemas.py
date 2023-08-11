from enum import StrEnum
from pydantic import BaseModel
from pydantic.generics import GenericModel
from typing import Generic, TypeVar


class ChatEvent(StrEnum):
    ROOM_JOIN = "room_join"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    ERROR = "error"
    MESSAGE = "message"


class ClientChatData(BaseModel):
    message: str = ""


class ChatData(BaseModel):
    message: str
    user: str
    time: str


class RoomJoinData(BaseModel):
    room_id: str
    messages: list[ChatData] = []
    users: list[str] = []


class UserJoinData(BaseModel):
    user: str


class UserLeaveData(BaseModel):
    user: str


DT = TypeVar('DT')


class ChatSocketBaseMessage(GenericModel, Generic[DT]):
    action: ChatEvent
    data: DT


class ChatSocketRoomJoinMessage(ChatSocketBaseMessage[RoomJoinData]):
    action = ChatEvent.ROOM_JOIN


class ChatSocketUserJoinMessage(ChatSocketBaseMessage[UserJoinData]):
    action = ChatEvent.USER_JOIN


class ChatSocketUserLeaveMessage(ChatSocketBaseMessage[UserLeaveData]):
    action = ChatEvent.USER_LEAVE


class ChatSocketChatMessage(ChatSocketBaseMessage[ChatData]):
    action = ChatEvent.MESSAGE


class ClientChatMessage(ChatSocketBaseMessage[ClientChatData]):
    # from Client
    action = ChatEvent.MESSAGE
