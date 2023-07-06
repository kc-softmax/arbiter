from datetime import datetime
from typing import Optional
from enum import StrEnum

from sqlmodel import Column, Field, SQLModel, String


class Role(StrEnum):
    OWNER = "owner"
    MAINTAINER = "maintainer"
    GAMER = "gamer"


class LoginType(StrEnum):
    GUEST = "guest"
    EMAIL = "email"
    FACEBOOK = "facebook"
    APPLE = "apple"
    STEAM = "steam"
    GOOGLE = "google"


class PKModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)


class TimestampModel(SQLModel):
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False
    )

    deprecated_at: datetime = Field(
        nullable=True
    )


class CommonModel(SQLModel):
    deprecated: bool = False


class User(PKModel, TimestampModel, CommonModel, table=True):
    __tablename__ = "user"
    email: Optional[str] = Field(sa_column=Column(String(128), unique=True))
    password: Optional[str] = Field(sa_column=Column(String(128)))
    display_name: Optional[str] = Field(sa_column=Column(String(128)))
    device_id: Optional[str] = Field(sa_column=Column(String(128), unique=True))
    login_type: LoginType = LoginType.GUEST
    access_token: Optional[str] = Field(sa_column=Column(String(128)))
    refresh_token: Optional[str] = Field(sa_column=Column(String(128)))


class ConsoleUser(PKModel, TimestampModel, CommonModel, table=True):
    __tablename__ = "console_user"
    email: str = Field(sa_column=Column(String(128), unique=True))
    password: str = Field(sa_column=Column(String(128)))
    user_name: str = Field(sa_column=Column(String(128)))
    role: Role = Role.GAMER
