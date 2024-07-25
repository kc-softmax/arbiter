import asyncio
from datetime import datetime
from pydantic import BaseModel
from typing import AsyncGenerator
from arbiter.service import RedisService
from arbiter.constants.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.broker import (
    subscribe_task, 
    periodic_task, 
    http_task, 
    stream_task,
)


class DefaultResponseModel(BaseModel):
    response: str

class TestModel(BaseModel):
    name: str
    age: int
    time: datetime

class TestService(RedisService):

    @subscribe_task(channel='test')
    async def on_message_test(self, message: bytes):
        print(f"on_message_test: {message}")

    @subscribe_task(channel='game')
    async def on_message_game(self, message: bytes):
        print(f"on_message_test: {message}")
        pass

    @periodic_task(period=5)  # TODO optioanlq
    async def hello_world(self, messages: list[bytes]):
        pass
        # print(f"hello_world: {messages}")

    @http_task(method=HttpMethod.POST)
    async def get_message_auth_no_request(self) -> DefaultResponseModel:
        return 'hihi'
    
    @http_task(method=HttpMethod.POST, response_model=TestModel)
    async def get_message(self, message: list[TestModel], member: list[int]) -> list[TestModel]:
        return message[0]
    
    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.ASYNC_UNICAST)
    async def on_stream(self, message: str) -> AsyncGenerator[str, None]:
        yield message

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.SYNC_UNICAST,
        auth=True)
    async def whisper(self, message: str) -> str:
        return message

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.BROADCAST)
    async def trade(self, message: str) -> str:
        return message

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.BROADCAST,
        num_of_channels=5)
    async def village(self, message: str) -> str:
        return message

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.BROADCAST)
    async def world(self, message: str) -> str:
        return message
        
        

