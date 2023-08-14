from datetime import datetime
from enum import StrEnum
from sqlmodel import Column, Field, SQLModel, String


class ConsoleRole(StrEnum):
    OWNER = "owner"
    MAINTAINER = "maintainer"


class LoginType(StrEnum):
    GUEST = "guest"
    EMAIL = "email"
    FACEBOOK = "facebook"
    APPLE = "apple"
    STEAM = "steam"
    GOOGLE = "google"


class PKModel(SQLModel):
    id: int | None = Field(default=None, primary_key=True)


class TimestampModel(SQLModel):
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )
    deprecated_at: datetime | None = Field(
        nullable=True
    )


class CommonUserBase(SQLModel):
    email: str | None = Field(sa_column=Column(String(128), unique=True))
    password: str | None = Field(sa_column=Column(String(128)))
    user_name: str | None = Field(sa_column=Column(String(128)))
    access_token: str | None = Field(sa_column=Column(String(128)))
    refresh_token: str | None = Field(sa_column=Column(String(128)))
    deprecated: bool = False


class UserBase(CommonUserBase, TimestampModel):
    device_id: str | None = Field(sa_column=Column(String(128), unique=True))
    login_type: LoginType = LoginType.GUEST


class ConsoleUserBase(CommonUserBase, TimestampModel):
    role: ConsoleRole = ConsoleRole.MAINTAINER


class User(PKModel, UserBase, table=True):
    __tablename__ = "user"


class ConsoleUser(PKModel, ConsoleUserBase, table=True):
    __tablename__ = "console_user"
