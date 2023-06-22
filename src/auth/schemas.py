from pydantic import BaseModel
from datetime import datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str


class TokenData(BaseModel):
    email: str
    exp: int


class User(BaseModel):
    email: str | None = None


class UserInDB(User):
    id: str
    hashed_password: str


class CreateUserRequest(BaseModel):
    email: str
    password: str


class CreateUserResponse(BaseModel):
    id: str
