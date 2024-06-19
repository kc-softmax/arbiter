import uvicorn
import aiohttp

import random
import asyncio


class ArbiterProxy:

    """
    This object manage routing target.
    You can add target or release target using proxy server
    """

    def __init__(self) -> None:
        self.targets: list[str] = []
        self.count = 0

    def get_targets(self) -> list[str]:
        return self.targets

    def find_target(self, target: str) -> bool:
        return True if target in self.targets else False

    def add_target(self, target: str) -> None:
        self.targets.append(target)

    def remove_target(self, target: str) -> None:
        self.targets.remove(target)


arbiter_proxy = ArbiterProxy()


async def send_to_server(server: aiohttp.ClientWebSocketResponse, receive):
    while True:
        message = await receive()
        if message['type'] == 'websocket.startup':
            ... # Do some startup here!
            # await send({'type': 'lifespan.startup.complete'})
        elif message['type'] == 'websocket.shutdown':
            ... # Do some shutdown here!
            # await send({'type': 'lifespan.shutdown.complete'})
            return
        elif message['type'] == 'websocket.disconnect':
            break
        elif message['type'] == 'websocket.receive':
            await server.send_bytes(message['bytes'])


async def send_to_client(send, server: aiohttp.ClientWebSocketResponse):
    async for server_msg in server:
        message = {
            'type': 'websocket.send',
            'bytes': server_msg.data
        }
        await send(message)


async def app(scope, receive, send):
    arbiter_proxy.count += 1
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                ... # Do some startup here!
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                ... # Do some shutdown here!
                await send({'type': 'lifespan.shutdown.complete'})
                return
    elif scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
            ],
        })
        if targets := arbiter_proxy.get_targets():
            async with aiohttp.ClientSession() as session:
                if scope['method'] == 'POST':
                    message = await receive()
                    async with session.post(
                        url=f'{targets[arbiter_proxy.count % 2]}{scope["path"]}',
                        data=message['body'].decode(),
                        headers={'content-type': 'application/json'}
                    ) as response:
                        res = await response.text()
                else:
                    async with session.get(
                        url=f'{targets[arbiter_proxy.count % 2]}{scope["path"]}',
                        headers={'content-type': 'application/json'}
                    ) as response:
                        res = await response.text()
            await send({
                'type': 'http.response.body',
                'body': res.encode(),
            })
        else:
            await send({
                'type': 'http.response.body',
                'body': b'Not valid arbiter',
            })
    else:
        await send({'type': 'websocket.accept'})
        if targets := arbiter_proxy.get_targets():
            base_url = targets[arbiter_proxy.count % 2]
            session = aiohttp.ClientSession()
            async with session.ws_connect(f"{base_url}{scope['path']}") as server_websocket:
                task1 = asyncio.create_task(send_to_server(server_websocket, receive))
                task2 = asyncio.create_task(send_to_client(send, server_websocket))
                try:
                    done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
                except:
                    print(done, pending)
        

if __name__ == "__main__":
    uvicorn.run("proxy_server:app", host='0.0.0.0', port=8000, log_level="info", reload=True)
