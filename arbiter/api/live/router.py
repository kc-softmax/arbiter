import asyncio

from fastapi import Query
from fastapi import APIRouter
from starlette.websockets import WebSocket

from arbiter.api.live.service import LiveService
from arbiter.api.live.engine import LiveAsyncEnvEngine


frame_rate = 30
router = APIRouter(prefix="/live")
live_async_env_engine = LiveAsyncEnvEngine(
    env_id='DI-v1',
    entry_point="maenv.dusty.dusty_env:DustyEnv",
    frame_rate=frame_rate
)
live_service = LiveService(live_async_env_engine)


"""
    message
    LiveMessage(
        src: 메시지를 보내는 주체
        target: 메시지를 받는 대상(없으면 broadcast)
        data: 채팅 내용 혹은 게임의 액션
        LiveSystemEvent: JOIN, LEAVE 등 목적에 맞는 처리
    )
"""


@router.websocket("/chat")
async def play_chat(websocket: WebSocket, user_id: str = Query(), team: int = Query(default=501), use_adapter: bool = Query(default=False)):
    async with live_service.connect(websocket, user_id, team, use_adapter) as user_info:
        try:
            user_id, user_name = user_info
            await live_service.publish_to_engine(websocket, user_id, use_adapter)
        except Exception as err:
            print(err)


@router.websocket("/game")
async def play_game(websocket: WebSocket, user_id: str = Query(), team: int = Query(default=501), use_adapter: bool = Query(default=False)):
    async with live_service.connect(websocket, user_id, team, use_adapter) as user_info:
        try:
            user_id, user_name = user_info
            await live_service.publish_to_engine(websocket, user_id, use_adapter)
        except Exception as err:
            print(err)
