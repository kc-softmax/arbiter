from arbiter.api.repository import (
    BaseCRUDRepository,
    func,
    select,
    AsyncSession,
    T,
)
from arbiter.api.match.models import GameRooms, GameAccess, UserState


class GameRoomsRepository(BaseCRUDRepository[GameRooms]):
    def __init__(self) -> None:
        super().__init__(GameRooms)

    async def get_join_list_by(self, session: AsyncSession, join_model) -> list[T]:
        stmt = select(self._model_cls.game_id).join(join_model
            ).where(join_model.user_state == UserState.JOIN
            ).group_by(self._model_cls.id, self._model_cls.max_player
            ).having(func.count() < self._model_cls.max_player
        )
        return (await session.exec(stmt)).all()


class GameAccessRepository(BaseCRUDRepository[GameAccess]):
    def __init__(self) -> None:
        super().__init__(GameAccess)


game_rooms_repository = GameRoomsRepository()
game_access_repository = GameAccessRepository()
