from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from starlette.concurrency import run_until_first_complete
from classic_snake_env.agents.agent import Snake
from classic_snake_env.const import GameState
from classic_snake_env.snake_env import SnakeEnv
from typing import Dict, Any
import asyncio
import names

from server.adapter import GymAdapter
from reference.service import Room, RoomManager


router = APIRouter(prefix="/ws/game")
room_manager = RoomManager()


async def server_event(room: Room, websocket: WebSocket, room_id: str, user_id: str) -> None:
    # 처음 들어왔을 때에는 ACTIVE상태가 아니기 때문에 움직이지 않는다
    # 3초 후에 모두 다같이 시작한다.
    snake: Snake = room.adapter.env.snakes[user_id]
    while True:
        await asyncio.sleep(0.1)
        if snake.state != GameState.ACTIVE and room.number_of_player[room_id] == room.maximum_players:
            await asyncio.sleep(3)
            snake.state = GameState.ACTIVE
        else:
            # TODO: obs는 array로 되어있어서 client에 그대로 보낼지 생각해봐야겠다.
            try:
                data = room.adapter.message.get_nowait()
            except asyncio.QueueEmpty as err:
                pass
            data = {
                agent_id: snake.body
                for agent_id, snake in room.adapters[room_id].env.snakes.items() if snake.is_alive
            }
            data['event'] = 'play'
            data['items'] = room.adapter.env.game_items.items
            await websocket.send_json(data)


async def client_event(websocket: WebSocket, room: Room) -> None:
    # 한 게임에 들어올 수 있는 숫자를 정의한다 현재는 2명
    # 최대 인원수가 들어오면 게임을 시작한다
    if len(room.clients) == room.maximum_players:
        asyncio.create_task(room.adapter.run())
        room.game_state = True
    while True:
        # 클라이언트가 나갔을 때 exception 처리가 되어 종료된다
        try:
            # client로 부터 받은 action을 queue에 넣는다
            data: Dict[str, Any] = await websocket.receive_json()
            if data.get('action') and room.game_state:
                client_id: int | str = data['name']
                action: int = data['action']
                room.adapter.add_user_message(client_id, action)
        except Exception:
            print('client left the room')
            break


@router.websocket("/{room_id}")
async def game_engine(websocket: WebSocket, room_id: str):
    await websocket.accept()
    user_id = names.get_first_name()
    
    # check available room and create room if not exist
    available_room = room_manager.find_available_room()
    if available_room:
        available_room.join_room(room_id, user_id, websocket)
    else:
        snake_env = SnakeEnv()
        adapter = GymAdapter(snake_env)
        available_room = room_manager.create_room(room_id, adapter)
        available_room.join_room(room_id, user_id, websocket)
    
    # user가 입장하면 join 이벤트를 보낸다.
    await websocket.send_json({'user_id': user_id, 'event': 'join'})
    
    # client에서 보내는 이벤트를 받는 태스크와 server 보내는 이벤트 태스크를 생성
    await run_until_first_complete(
        (server_event, {'websocket': websocket, 'room_id': room_id, 'user_id': user_id}),
        (client_event, {'websocket': websocket, 'room_id': room_id, 'user_id': user_id}),
    )
    
    # 클라이언트가 나간 것으로 간주
    available_room.leave_room(user_id)
