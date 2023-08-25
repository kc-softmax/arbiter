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
    ROOM_CHANGE = "room_change"


class ClientChatData(BaseModel):
    message: str = ""


class ErrorData(BaseModel):
    code: int
    reason: str


class UserData(BaseModel):
    user_id: int
    user_name: str


class ChatData(BaseModel):
    message: str
    message_id: int = 0
    user: UserData
    time: str


class RoomJoinData(BaseModel):
    room_id: str
    messages: list[ChatData] = []
    number_of_users: int = 0
    users: list[UserData] = []


class UserJoinData(BaseModel):
    user: UserData


class UserLeaveData(BaseModel):
    user: UserData


class RoomChangeData(BaseModel):
    room_id: str


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


class ChatSocketErrorMessage(ChatSocketBaseMessage[ErrorData]):
    action = ChatEvent.ERROR


class ClientChatMessage(ChatSocketBaseMessage[ClientChatData]):
    # from Client
    action = ChatEvent.MESSAGE
