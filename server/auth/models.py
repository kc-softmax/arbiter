from datetime import datetime
from typing import Optional
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

    deprecated_at: Optional[datetime] = Field(
        nullable=True
    )


class CommonModel(SQLModel):
    deprecated: bool = False


class CommonUserBase(SQLModel):
    email: Optional[str] = Field(sa_column=Column(String(128), unique=True))
    password: Optional[str] = Field(sa_column=Column(String(128)))
    user_name: Optional[str] = Field(sa_column=Column(String(128)))
    access_token: Optional[str] = Field(sa_column=Column(String(128)))
    refresh_token: Optional[str] = Field(sa_column=Column(String(128)))


class UserBase(CommonUserBase, TimestampModel, CommonModel):
    device_id: Optional[str] = Field(sa_column=Column(String(128), unique=True))
    login_type: Optional[LoginType] = LoginType.GUEST


class ConsoleUserBase(CommonUserBase, TimestampModel, CommonModel):
    role: Optional[ConsoleRole] = ConsoleRole.MAINTAINER


class User(PKModel, UserBase, table=True):
    __tablename__ = "user"


class ConsoleUser(PKModel, ConsoleUserBase, table=True):
    __tablename__ = "console_user"
