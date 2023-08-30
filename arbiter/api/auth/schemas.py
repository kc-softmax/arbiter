from pydantic import BaseModel

from arbiter.api.auth.models import UserBase, ConsoleUserBase, PKModel


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


class GamerUserSchema(UserBase):
    class Config:
        omit_fields = {"password", "access_token", "refresh_token"}


class GamerUserCreateByEmail(UserBase):
    class Config:
        pick_fields = {"email", "password"}


class GamerUserUpdate(UserBase):
    class Config:
        pick_fields = {"user_name"}


class GamerUserLoginByGuest(UserBase):
    class Config:
        pick_fields = {"device_id"}


class ConsoleUserSchema(ConsoleUserBase):
    class Config:
        omit_fields = {"password", "access_token", "refresh_token"}


class ConsoleUserGet(PKModel):
    pass


class ConsoleUserCreate(ConsoleUserBase):
    class Config:
        pick_fields = {"email", "password", "user_name", "role"}


class ConsoleUserUpdate(ConsoleUserBase, PKModel):
    class Config:
        pick_fields = {"id", "email",  "password", "user_name", "role"}
