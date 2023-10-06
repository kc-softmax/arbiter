from sqlmodel import select
from arbiter.api.repository import BaseCRUDRepository
from arbiter.example.models import GameRound, GameScore


# 새로 추가한 db table에 대한 repository 생성
class GameRoundRepository(BaseCRUDRepository[GameRound]):
    def __init__(self) -> None:
        super().__init__(GameRound)


class GameScoreRepository(BaseCRUDRepository[GameScore]):
    def __init__(self) -> None:
        super().__init__(GameScore)

    async def get_score_by_user_id(self, user_id: int):
        return await self.get_one_by(user_id=user_id)

    async def get_scores_by_round_id(self, round_id: int):
        stmt = (
            select(GameScore)
            .join(GameRound)
            .where(GameScore.round_id == round_id)
        )
        return (await self.session.exec(stmt)).all()


game_round_repository = GameRoundRepository()
game_score_repository = GameScoreRepository()
