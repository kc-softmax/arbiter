from pydantic import BaseModel

from server.utils import Pick, Omit
from server.auth.models import ConsoleUserBase, UserBase


class SingleId(BaseModel):
    id: str


class ConsoleRequest(BaseModel):
    is_console: bool = False


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    sub: str
    exp: int


class TokenRefreshRequest(TokenSchema, ConsoleRequest):
    pass


class GamerUserSchema(SingleId, UserBase, metaclass=Omit):
    class Config:
        omit_fields = {"password"}


class GamerUserCreateByEmail(UserBase, metaclass=Pick):
    class Config:
        pick_fields = {"email", "password"}


class GamerUserUpdate(UserBase, metaclass=Pick):
    class Config:
        pick_fields = {"user_name"}


class GamerUserLoginByGuest(UserBase, metaclass=Pick):
    class Config:
        pick_fields = {"device_id"}


class ConsoleUserSchema(SingleId, ConsoleUserBase, metaclass=Omit):
    class Config:
        omit_fields = {"password", "access_token", "refresh_token"}


class ConsoleUserGet(SingleId):
    pass


class ConsoleUserCreate(ConsoleUserBase, metaclass=Pick):
    class Config:
        pick_fields = {"email", "password", "user_name", "role"}


class ConsoleUserUpdate(SingleId, ConsoleUserBase, metaclass=Pick):
    class Config:
        pick_fields = {"id", "email", "user_name", "role"}
