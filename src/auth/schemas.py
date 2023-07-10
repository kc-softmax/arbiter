from pydantic import BaseModel

from auth.models import LoginType


class UserSchema(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    device_id: str | None = None
    login_type: LoginType


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    sub: str
    exp: int
    login_type: LoginType


class CreateEmailUserRequest(BaseModel):
    email: str
    password: str


class UpdateUserRequest(BaseModel):
    display_name: str


class LoginGuestUserRequest(BaseModel):
    device_id: str
