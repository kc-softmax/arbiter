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
    access_token: str | None
    refresh_token: str | None


class UserCreate(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    email: str
    description: str | None
    access_token: str | None
    refresh_token: str | None
