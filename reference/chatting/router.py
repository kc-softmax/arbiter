from fastapi import Request, Response
from fastapi.routing import APIRouter
from starlette.websockets import WebSocket
from starlette.concurrency import run_until_first_complete
import asyncio

from server.adapter import ChatAdapter
from reference.service import Room
from reference.chatting.chatting_env import ChattingEnv
from reference.chatting.chat_user import ChatUser


router = APIRouter(prefix="/ws/chat")
room = Room()


@router.post("/register")
async def register_user(user: Request, response: Response):
    # response.set_cookie(key="X-Authorization", value=user.username, httponly=True)
    pass


async def send_broadcast_message(adapter: ChatAdapter, clients: dict[str, WebSocket]):
    while True:
        await asyncio.sleep(0.01)
        try:
            async with adapter.get() as message:
                if message:
                    data = {
                        'sender': list(message.keys())[0],
                        'message': list(message.values())[0]
                    }
                    for _, other_websocket in clients.items():
                        await other_websocket.send_json(data)
        except Exception as err:
            pass


async def receive_message(chat_user: ChatUser, adapter: ChatAdapter, websocket: WebSocket):
    while True:
        try:
            data = await websocket.receive_json()
            client_id: str = data['sender']
            client_message: str = data['message']
            adapter.add_client_action(client_id, client_message)
        except Exception as err:
            chat_user.is_leave = True
            print('client leave the room')
            break


@router.websocket("/room/{room_id}")
async def chat_engine(websocket: WebSocket, room_id: str):
    await websocket.accept()
    init: dict(str | int, str) = await websocket.receive_json()
    sender: str = init['sender']
    chat_user: ChatUser = ChatUser(sender)
    
    # check available room and create room if not exist
    if room.adapters.get(room_id) and not room.game_state[room_id]:
        is_join = room.join_room(room_id, sender, chat_user, websocket)
        if not is_join:
            await websocket.close()
            return
    else:
        chat_env = ChattingEnv([chat_user])
        adapter = ChatAdapter(chat_env)
        room.attach_adapter(room_id, adapter)
        room.join_room(room_id, sender, chat_user, websocket)
        asyncio.create_task(room.adapters[room_id].run())
        
    await run_until_first_complete(
        (
            receive_message, {
                'chat_user': chat_user,
                'adapter': room.adapters[room_id],
                'websocket': websocket
            }
        ),
        (
            send_broadcast_message, {
                'adapter': room.adapters[room_id],
                'clients': room.clients[room_id]
            }
        ),
    )
