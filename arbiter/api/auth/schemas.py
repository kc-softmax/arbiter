from pydantic import BaseModel

from arbiter.api.auth.models import GameUserBase, PKModel


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    sub: str
    exp: int


class TokenRefreshRequest(TokenSchema):
    pass


class GamerUserSchema(GameUserBase, PKModel):
    class Config:
        omit_fields = {"password"}


class GamerUserCreateByEmail(GameUserBase):
    class Config:
        pick_fields = {"user_name", "email", "password", "adapter"}


class GamerUserUpdate(GameUserBase):
    class Config:
        pick_fields = {"user_name"}


class GamerUserLoginByGuest(GameUserBase):
    class Config:
        pick_fields = {"device_id"}

GamerUserLoginByUserName = GamerUserUpdate