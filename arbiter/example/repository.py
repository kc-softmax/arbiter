from sqlmodel import Column, Field, String

from arbiter.api.auth.models import PKModel
from arbiter.api.repository import BaseCRUDRepository


# orm table class 정의
class Match(PKModel, table=True):
    __tablename__ = "match"
    team: str | None = Field(sa_column=Column(String(128)))


# 새로 추가한 db table에 대한 repository 생성
class MatchRepository(BaseCRUDRepository[Match]):
    def __init__(self) -> None:
        super().__init__(Match)

    def get_match():
        pass


match_repoitory = MatchRepository()
