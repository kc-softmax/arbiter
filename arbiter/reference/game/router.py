from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from classic_snake_env.agents.agent import Snake
from classic_snake_env.const import GameState
from classic_snake_env.snake_env import SnakeEnv
import asyncio
import names

from arbiter.api.adapter import GymAdapter
from reference.game.room import Room, RoomManager


router = APIRouter(prefix="/ws/game")
room_manager = RoomManager()


async def server_event(room: Room) -> None:
    async with room.adapter.subscribe() as game_data:
        async for _ in game_data:
            for _, client in room.clients.items():
                data = {
                    agent_id: snake.body
                    for agent_id, snake in room.adapter.env.snakes.items() if snake.is_alive
                }
                data['event'] = 'play'
                data['items'] = room.adapter.env.game_items.items
                await client.send_json(data)


async def game_starter(room: Room, user_id: str) -> None:
    snake = room.adapter.env.snakes[user_id]
    while True:
        # client로 부터 받은 action을 queue에 넣는다
        if snake.state != GameState.ACTIVE and room.number_of_player == room.maximum_players:
            await asyncio.sleep(3)
            snake.state = GameState.ACTIVE
            break


async def client_event(websocket: WebSocket, room: Room) -> None:
    while True:
        # 클라이언트가 나갔을 때 exception 처리가 되어 종료된다
        try:
            # client로 부터 받은 action을 queue에 넣는다
            data: dict[str, any] = await websocket.receive_json()
            if data.get('action'):
                client_id: int | str = data['name']
                action: int = data['action']
                room.adapter.add_user_message(client_id, action)
                new_obs = await room.adapter.execute()
                await room.adapter._queue.put(new_obs)
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
        asyncio.create_task(server_event(available_room))

    # user가 입장하면 join 이벤트를 보낸다.
    await websocket.send_json({'user_id': user_id, 'event': 'join'})

    # client에서 보내는 이벤트를 받는 태스크와 server 보내는 이벤트 태스크를 생성
    client = asyncio.create_task(client_event(websocket, available_room, user_id))
    game = asyncio.create_task(game_starter(available_room, user_id))
    await game
    await client

    # 클라이언트가 나간 것으로 간주
    available_room.leave_room(user_id)
    if available_room.number_of_player == 0:
        await available_room.adapter._queue.put(None)
        room_manager.remove_room(room_id)
