from .adapter import Adapter
from .service import Room

from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from starlette.concurrency import run_until_first_complete
from classic_snake_env.agents.agent import Snake
from classic_snake_env.const import GameState
from classic_snake_env.snake_env import SnakeEnv
from typing import Dict, Any
import asyncio
import names


router = APIRouter(prefix="/ws/game")
room = Room()


async def server_event(room_id: str, user_name: str) -> None:
    # 처음 들어왔을 때에는 ACTIVE상태가 아니기 때문에 움직이지 않는다
    # 3초 후에 모두 다같이 시작한다.
    # 어떻게 해야할지 생각해봐야겠다...
    snake: Snake = room.adapter[room_id].env.snakes[user_name]
    while True:
        await asyncio.sleep(0.01)
        if snake.state != GameState.ACTIVE and room.number_of_player[room_id] == 2:
            await asyncio.sleep(3)
            snake.state = GameState.ACTIVE


async def client_event(room_id: str, user_name: str) -> None:
    # 한 게임에 들어올 수 있는 숫자를 정의한다 현재는 2명
    # 최대 인원수가 들어오면 게임을 시작한다
    if room.number_of_player[room_id] == 2:
        asyncio.create_task(room.adapter[room_id].run())
        room.adapter[room_id].is_started = True
    websocket: WebSocket = room.adapter[room_id].clients[user_name]
    while True:
        # 클라이언트가 나갔을 때 exception 처리가 되어 종료된다
        try:
            data: Dict[str, Any] = await websocket.receive_json()
            if data.get('action'):
                room.adapter[room_id].update_player_action(data['name'], data['action'])
        except Exception:
            print('client left the room')
            break


@router.websocket("/{room_id}")
async def main(websocket: WebSocket, room_id: str):
    await websocket.accept()
    user_name = names.get_first_name()
    
    # check available room and create room if not exist
    if room.adapter.get(room_id) and not room.adapter[room_id].is_started:
        room.join_room(room_id, user_name, websocket)
    else:
        snake_env = SnakeEnv()
        adapter = Adapter(snake_env)
        room.attach_adapter(room_id, adapter)
        room.join_room(room_id, user_name, websocket)
    
    # user가 입장하면 join 이벤트를 보낸다.
    await websocket.send_json({'name': user_name, 'event': 'join'})
    
    # client에서 보내는 이벤트를 받는 태스크와 server 보내는 이벤트 태스크를 생성
    await run_until_first_complete(
        (server_event, {'room_id': room_id, 'user_name': user_name}),
        (client_event, {'room_id': room_id, 'user_name': user_name}),
    )
    
    # 클라이언트가 나간 것으로 간주
    room.leave_room(room_id)
    