from arbiter.api.repository import (
    BaseCRUDRepository,
    SelectOfScalar,
    func,
    select,
    AsyncSession,
    T,
)
from arbiter.api.match.models import GameRooms, GameAccess, GameState, UserState


class GameRoomsRepository(BaseCRUDRepository[GameRooms]):
    def __init__(self) -> None:
        super().__init__(GameRooms)

    def _construct_with_join_group_by_stmt(self, join_model) -> SelectOfScalar:
        stmt = select(self._model_cls.id).join(join_model
            ).where(self._model_cls.game_state == GameState.AVAILABLE,
                    join_model.user_state == UserState.JOIN
            ).group_by(self._model_cls.id, self._model_cls.max_players
            ).having(func.count() < self._model_cls.max_players
        )
        return stmt

    async def get_join_list_by(self, session: AsyncSession, join_model) -> list[T]:
        stmt = self._construct_with_join_group_by_stmt(join_model)
        return (await session.exec(stmt)).all()


class GameAccessRepository(BaseCRUDRepository[GameAccess]):
    def __init__(self) -> None:
        super().__init__(GameAccess)


game_rooms_repository = GameRoomsRepository()
game_access_repository = GameAccessRepository()
