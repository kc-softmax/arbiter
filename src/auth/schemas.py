from pydantic import BaseModel


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str


class TokenDataSchema(BaseModel):
    email: str
    exp: int


class UserSchema(BaseModel):
    id: str
    email: str | None = None


class CreateUserRequest(BaseModel):
    email: str
    password: str


class UserInDB(BaseModel):  # TODO model의 User 이용
    id: str
    email: str | None = None
    hashed_password: str
