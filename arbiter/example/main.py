from datetime import datetime
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

import arbiter.api.auth.repository as ArbiterAuthRepo
import arbiter.example.repository as MyRepo
from arbiter.api.auth.models import GameUser
from arbiter.api.auth.dependencies import get_current_user
from arbiter.api.dependencies import unit_of_work
from arbiter.api.main import app

# 사용할 레포지토리 리스트
repositories = [
    MyRepo.game_round_repository,
    MyRepo.game_score_repository,
    ArbiterAuthRepo.game_uesr_repository
]

# 자신의 APIRouter를 생성한다.
# 이 때, 사용할 레포지토리를 포함한 UnitOfWork를 디펜던시로 포함시켜준다.
router = APIRouter(
    prefix="/example",
)


# API 구현
@router.post("/game/score")
async def save_game_score(
    user:GameUser = Depends(get_current_user),
    session: AsyncSession = Depends(unit_of_work)
):
    # 스코어 데이터는 해당 라운드에 대한 데이터가 db에 먼저 있어야한다.(외래키 제약)
    # 게임이 시작?될 때 round를 먼저 저장해야할까?
    # 그럼 게임이 끝나기 전 유저의 스코어 데이터는 어떻게 저장해야 할까?
    # - 게임이 시작되면 일단 해당 게임의 라운드 데이터를 저장하고 나중에 다른 내역들을 업데이트하는 방법으로 해야할까?
    round = MyRepo.GameRound(
        name="test",
        started_at=datetime.utcnow(),
        ended_at=datetime.utcnow()
    )
    await MyRepo.game_round_repository.add(session, round)

    score = MyRepo.GameScore(
        user_id=user.id,
        round_id=round.id,
        kill_count=1,
        death_count=2,
        domination_count=100
    )
    await MyRepo.game_score_repository.add(session, score)    
    
    return score

# 생성한 Router를 가장 상위 fastapi 서비스(app)에 포함시켜준다.
app.include_router(router)
