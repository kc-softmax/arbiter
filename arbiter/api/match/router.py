import uuid

from enum import Enum
from fastapi.routing import APIRouter
from fastapi import Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from arbiter.api.match.models import GameRooms, GameAccess
from arbiter.api.match.repository import game_rooms_repository, game_access_repository
from arbiter.api.dependencies import unit_of_work
from arbiter.api.auth.utils import verify_token
from arbiter.api.match.schemas import MatchGameSchema


repositories = [game_rooms_repository, game_access_repository]


class MatchRouterTag(str, Enum):
    ROOM = "Match(Room)"


router = APIRouter(
    prefix="/match"
)


@router.post(
    path="/game",
    tags=MatchRouterTag.ROOM,
    response_model=int
)
async def matchmaking(data: MatchGameSchema, session: AsyncSession = Depends(unit_of_work)):
    # user 검사 한번 더
    _ = verify_token(data.token)
    # 게임방의 available 상태와 유저의 join에 따라 max_players미만인 게임만 탐색한다
    # 게임방 상태는 체크할 필요가 없어도 될 것 같다(max_players가 넘어가면 조회되지 않음)
    # 첫 번째 게임방을 접속시킨다
    # DELETE는 하지 않고 INSERT, 상태 UPDATE로 게임 접속유저 데이터를 관리한다
    # game_id를 uuid로 할지 DB의 pk값으로 할지 정해야한다(현재는 pk값, uuid는 임시로 추가)
    # schema의 관계는 game_access가 game_rooms 테이블의 id(pk)를 외래키로 사용
    # client에서는 wss://gametester.fourbarracks.io/di/ws?token=&game_id= 로 붙여서 호출
    # gmae-server-engine에서는 game_id에 따라 live_service를 새로 실행하거나 실행된 live_service를 리턴
    available_game_ids = await game_rooms_repository.get_join_list_by(session, GameAccess)
    if available_game_ids:
        record = await game_rooms_repository.get_by_id(
            session,
            available_game_ids.pop(0)
        )
    else:
        game_id = uuid.uuid4()
        record = await game_rooms_repository.add(session,
            GameRooms(
                game_id=str(game_id),
                max_player=4,
            )
        )
    # user 추가는 game server engine에서 접속했을 때 한다
    print(record.id)
    return record.id
