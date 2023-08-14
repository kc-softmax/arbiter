from pydantic import BaseModel

from server.utils import Pick, Omit
from server.auth.models import UserBase, ConsoleUserBase, PKModel


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    sub: str
    exp: int


class ConsoleRequest(BaseModel):
    is_console: bool = True


class TokenRefreshRequest(TokenSchema, ConsoleRequest):
    pass


class GamerUserSchema(UserBase, metaclass=Omit):
    class Config:
        omit_fields = {"password", "access_token", "refresh_token"}


class GamerUserCreateByEmail(UserBase, metaclass=Pick):
    class Config:
        pick_fields = {"email", "password"}


class GamerUserUpdate(UserBase, metaclass=Pick):
    class Config:
        pick_fields = {"user_name"}


class GamerUserLoginByGuest(UserBase, metaclass=Pick):
    class Config:
        pick_fields = {"device_id"}


class ConsoleUserSchema(ConsoleUserBase, metaclass=Omit):
    class Config:
        omit_fields = {"password", "access_token", "refresh_token"}


class ConsoleUserGet(PKModel):
    pass


class ConsoleUserCreate(ConsoleUserBase, metaclass=Pick):
    class Config:
        pick_fields = {"email", "password", "user_name", "role"}


class ConsoleUserUpdate(ConsoleUserBase, PKModel, metaclass=Pick):
    class Config:
        pick_fields = {"id", "email",  "password", "user_name", "role"}
