from enum import Enum
from sqlmodel import Column, Field, String

from arbiter.api.models import PKModel, BaseSQLModel, TimestampModel


class LoginType(str, Enum):
    GUEST = "guest"
    EMAIL = "email"
    FACEBOOK = "facebook"
    APPLE = "apple"
    STEAM = "steam"
    GOOGLE = "google"
    TESTER = "tester"


# auth 도메인 모델들
class CommonUserBase(BaseSQLModel):
    email: str | None = Field(sa_column=Column(String(128), unique=True))
    password: str | None = Field(sa_column=Column(String(128)))
    user_name: str | None = Field(sa_column=Column(String(128)), unique=True)
    access_token: str | None = Field(sa_column=Column(String(128)))
    refresh_token: str | None = Field(sa_column=Column(String(128)))
    deprecated: bool = False
    player_token: str | None = Field(sa_column=Column(String(512)), unique=True)
    is_unlocked: bool = False

class GameUserBase(CommonUserBase, TimestampModel):
    device_id: str | None = Field(sa_column=Column(String(128), unique=True))
    login_type: LoginType = LoginType.GUEST
    adapter: str | None = Field(sa_column=Column(String(128)))


class GameUser(PKModel, GameUserBase, table=True):
    __tablename__ = "user"
