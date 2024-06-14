import random
import httpx
import aiohttp
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from starlette.websockets import WebSocket
from starlette.background import BackgroundTask
from pydantic import BaseModel


app = FastAPI()


class TargetRequest(BaseModel):
    target: str


class TargetResponse(BaseModel):
    code: int
    message: str


class ArbiterProxy:
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


@app.post("/register/target", response_model=TargetResponse)
async def add_target(request: TargetRequest):
    if arbiter_proxy.find_target(request.target):
        message = 'already registered'
    else:
        arbiter_proxy.add_target(request.target)
        message = 'added target'
    return TargetResponse(
        code=200,
        message=message
    )


@app.post("/release/target", response_model=TargetResponse)
async def release_target(request: TargetRequest):
    if arbiter_proxy.find_target(request.target):
        arbiter_proxy.remove_target(request.target)
        message = "released target"
    else:
        message = "Not found"
    return TargetResponse(
        code=200,
        message=message
    )


@app.post("/{full_path:path}")
async def stateless_connection(request: Request):
    base_url = random.choice(arbiter_proxy.get_targets())
    client = httpx.AsyncClient(base_url=base_url)
    url = httpx.URL(path=request.url.path,
                    query=request.url.query.encode("utf-8"))
    rp_req = client.build_request(request.method, url,
                                  headers=request.headers.raw,
                                  content=await request.body())
    rp_resp = await client.send(rp_req, stream=True)
    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=rp_resp.headers,
        background=BackgroundTask(rp_resp.aclose),
    )


async def send_to_server(server: aiohttp.ClientWebSocketResponse, client: WebSocket):
    async for client_msg in client.iter_bytes():
        await server.send_bytes(client_msg)


async def send_to_client(client: WebSocket, server: aiohttp.ClientWebSocketResponse):
    async for server_msg in server:
        await client.send_bytes(server_msg.data)


@app.websocket("/{full_path:path}")
async def stateful_connection(client_websocket: WebSocket, full_path: str):
    await client_websocket.accept()
    if targets := arbiter_proxy.get_targets():
        base_url = random.choice(targets)
        session = aiohttp.ClientSession()
        async with session.ws_connect(f"{base_url}{full_path}") as server_websocket:
            task1 = asyncio.create_task(send_to_server(server_websocket, client_websocket))
            task2 = asyncio.create_task(send_to_client(client_websocket, server_websocket))
            try:
                done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
            except:
                print(done, pending)
    
        await session.close()