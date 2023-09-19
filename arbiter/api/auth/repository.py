from arbiter.api.repository import BaseCRUDRepository
from arbiter.api.auth.models import User


class GamerUserRepository(BaseCRUDRepository[User]):
    def __init__(self) -> None:
        super().__init__(User)
