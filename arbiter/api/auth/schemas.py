from sqlalchemy import Column, String
from pydantic import BaseModel, Field


# class LoginType(str, Enum):
#     GUEST = "guest"
#     EMAIL = "email"
#     FACEBOOK = "facebook"
#     APPLE = "apple"
#     STEAM = "steam"
#     GOOGLE = "google"
#     TESTER = "tester"

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    sub: str
    exp: int


class TokenRefreshRequest(TokenSchema):
    pass


class UserSchema(BaseModel):
    id: int
    email: str
    password: str
    hash_tag: int
    access_token: str | None = Field(sa_column=Column(String(128)))
    refresh_token: str | None = Field(sa_column=Column(String(128)))


class UserCreate(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    email: str
    access_token: str = Field(sa_column=Column(String(128)))
    refresh_token: str = Field(sa_column=Column(String(128)))
