from fastapi import APIRouter, Depends

from arbiter.api.main import app
from arbiter.api.dependencies import UnitOfWork
import arbiter.api.auth.repository as ArbiterAuthRepo
import arbiter.example.repository as MyRepo

# 사용할 레포지토리 리스트
repositories = [
    MyRepo.match_repoitory,
    ArbiterAuthRepo.game_uesr_repository
]

# 자신의 APIRouter를 생성한다.
# 이 때, 사용할 레포지토리를 포함한 UnitOfWork를 디펜던시로 포함시켜준다.
router = APIRouter(
    prefix="/example",
    dependencies=[Depends(UnitOfWork(repositories))]
)


# API 구현
@router.get("/match")
async def add_match():
    match = MyRepo.Match(team="blue")
    await MyRepo.match_repoitory.add(match)
    return match

# 생성한 Router를 가장 상위 fastapi 서비스(app)에 포함시켜준다.
app.include_router(router)
