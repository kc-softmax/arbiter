from httpx import AsyncClient
from arbiter.api.config import settings


class GameTesterAPI:
    def __init__(self) -> None:
        self.client = AsyncClient(base_url="https://server.gametester.gg/dev-api/v1/")

    async def auth(self, player_pin: str) -> dict[str, any]:
        async with self.client as client:
            response = await client.post('auth', json={
                "developerToken": settings.GAME_TESTER_DEVELOPER_TOKEN,
                "playerPin": player_pin
            })
            return response.json()

    async def unlock(self, player_token: str) -> dict[str, any]:
        async with self.client as client:
            response = await client.post('unlock', json={
                "developerToken": settings.GAME_TESTER_DEVELOPER_TOKEN,
                "playerToken": player_token
            })
            return response.json()
