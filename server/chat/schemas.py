from enum import StrEnum
from pydantic import BaseModel
from pydantic.generics import GenericModel
from typing import Generic, TypeVar


# TODO: ChatEvent를 도메인별로 관리 되게
class ChatEvent(StrEnum):
    ROOM_JOIN = "room_join"
    USER_JOIN = "user_join"
    ROOM_LEAVE = "room_leave"
    USER_LEAVE = "user_leave"
    ERROR = "error"
    MESSAGE = "message"
    NOTICE = "notice"
    ROOM_CHANGE = "room_change"
    ROOM_CREATE = "room_create"
    LOBBY_REFRESH = "lobby_refresh"
    INVITEE_LIST = "invitee_list"
    USER_INVITE = "user_invite"
    MESSAGE_LIKE = "message_like"


class ClientChatData(BaseModel):
    room_id: str
    message: str


class ErrorData(BaseModel):
    code: int
    reason: str


class UserData(BaseModel):
    user_id: int
    user_name: str


# TODO: message 불러 올때 좋아요 싫어요
class ChatData(BaseModel):
    room_id: str
    message: str
    message_id: str
    user: UserData
    time: str
    like: int = 0


class MessageLikeData(BaseModel):
    room_id: str
    message_id: str
    like: int = 0


class RoomCurrentUserData(BaseModel):
    current: int
    max: int


class LobbyData(BaseModel):
    room_id: str
    current_users: int
    max_users: int


class RoomJoinData(BaseModel):
    room_id: str
    messages: list[ChatData] = []
    current_users: int
    max_users: int = 0
    users: list[UserData] = []
    notice: str = ""


class UserJoinData(BaseModel):
    room_id: str
    user: UserData


class UserLeaveData(BaseModel):
    room_id: str
    user: UserData


class UserInviteData(BaseModel):
    room_id: str
    user_name_from: str  # user_name


class RoomChangeData(BaseModel):
    room_id: str


class RoomCreateData(BaseModel):
    room_id: str
    # TODO: default 값 삭제
    max_users: int = 100
    
class InviteeData(BaseModel):
    user: UserData
    is_online: bool


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


class ChatSocketNoticeMessage(ChatSocketBaseMessage[ClientChatData]):
    action = ChatEvent.NOTICE


class ChatSocketRoomCreateMessage(ChatSocketBaseMessage[ClientChatData]):
    action = ChatEvent.ROOM_CREATE


class ChatSocketLobbyRefreshMessage(ChatSocketBaseMessage[list[LobbyData]]):
    action = ChatEvent.LOBBY_REFRESH


class ChatSocketUserInviteMessage(ChatSocketBaseMessage[UserInviteData]):
    action = ChatEvent.USER_INVITE


class ChatSocketUserLikeMessage(ChatSocketBaseMessage[MessageLikeData]):
    action = ChatEvent.MESSAGE_LIKE

class ChatSocketInviteeListMessage(ChatSocketBaseMessage[list[InviteeData]]):
    action = ChatEvent.INVITEE_LIST


class ClientChatMessage(ChatSocketBaseMessage[ClientChatData]):
    # from Client
    action = ChatEvent.MESSAGE
