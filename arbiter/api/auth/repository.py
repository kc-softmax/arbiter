from arbiter.api.repository import BaseCRUDRepository
from arbiter.api.auth.models import GameUser


class GameUserRepository(BaseCRUDRepository[GameUser]):
    def __init__(self) -> None:
        super().__init__(GameUser)


game_uesr_repository = GameUserRepository()
