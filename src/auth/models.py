from datetime import datetime
from typing import Optional
from database import engine
from sqlmodel import Column, Field, SQLModel, String
from enum import StrEnum

class LoginType(StrEnum):
    GUEST = "guest"
    EMAIL = "email"
    FACEBOOK = "facebook"
    APPLE = "apple"
    STEAM = "steam"
    GOOGLE = "google"


class User(SQLModel, table=True):
    __tablename__ = "user"
    # auto increment
    id: Optional[int] = Field(default=None, primary_key=True)
    email: Optional[str] = Field(sa_column=Column(String(128)), unique=True)
    password: Optional[str] = Field(sa_column=Column(String(128)))
    display_name: Optional[str] = Field(sa_column=Column(String(128)))
    device_id: Optional[str] = Field(sa_column=Column(String(128)))
    verified: bool = False
    login_type: Optional[LoginType] = LoginType.GUEST
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
