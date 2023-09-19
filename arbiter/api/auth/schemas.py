from pydantic import BaseModel

from arbiter.api.auth.models import UserBase, PKModel


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    sub: str
    exp: int


class TokenRefreshRequest(TokenSchema):
    pass


class GamerUserSchema(UserBase, PKModel):
    class Config:
        omit_fields = {"password"}


class GamerUserCreateByEmail(UserBase):
    class Config:
        pick_fields = {"email", "password"}


class GamerUserUpdate(UserBase):
    class Config:
        pick_fields = {"user_name"}


class GamerUserLoginByGuest(UserBase):
    class Config:
        pick_fields = {"device_id"}
