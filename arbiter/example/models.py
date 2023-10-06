from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from arbiter.api.auth.models import GameUser

from arbiter.api.models import PKModel


class GameRound(PKModel, table=True):
    __tablename__ = "game_round"
    name: str = Field(nullable=False)
    started_at: datetime = Field(nullable=False)
    ended_at: datetime = Field(nullable=False)
    # GameRound(부모 객체)에서 GameScore를 바로 접근하기 위해 back_populates 를 선언해준다.
    scores: list["GameScore"] | None = Relationship(
        back_populates="round",
        sa_relationship_kwargs={
            "lazy": "joined"
        }
    )


class GameScore(PKModel, table=True):
    __tablename__ = "game_score"
    user_id: int = Field(foreign_key="user.id")
    user: GameUser = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
        }
    )
    round_id: int = Field(foreign_key="game_round.id")
    round: GameRound = Relationship(
        back_populates="scores",
        sa_relationship_kwargs={
            "lazy": "joined",
        }
    )
    kill_count: int = Field(default=0)
    death_count: int = Field(default=0)
    domination_count: int = Field(default=0)
