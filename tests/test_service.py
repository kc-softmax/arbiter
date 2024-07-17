import asyncio
from pydantic import BaseModel
from typing import AsyncGenerator
from arbiter.broker import subscribe_task, periodic_task, http_task, stream_task
from arbiter.service import RedisService
from arbiter.constants.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.database import User



class TestModel(BaseModel):
    name: str
    age: int

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

    # @http_task(method=HttpMethod.POST, response_model=TestModel, auth=True)
    # async def get_message_auth(self, message: TestModel, member: int) -> TestModel:
    #     return message

    # @http_task(method=HttpMethod.POST, auth=True)
    # async def get_message_auth_no_request(self, user_id: int) -> str:
    #     return 'its me'
    
    @http_task(method=HttpMethod.POST, response_model=list[TestModel])
    async def get_message(self, message: list[TestModel], member: list[int]) -> list[TestModel]:
        return message
    
    # @http_task(method=HttpMethod.POST)
    # async def get_message_no_requset(self) -> int:
    #     return 486
    
    # @stream_task(
    #     connection=StreamMethod.WEBSOCKET,
    #     communication_type=StreamCommunicationType.ASYNC_UNICAST)
    # async def get_message_async_unit_cast(self, message: str) -> AsyncGenerator[str, None]:
    #     yield 'hiu' + message
        
    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.MULTICAST)
    async def get_message_multicast(self, message: str) -> str:
        # target을 
        # 사용자가 관여하는 부분은 이 부분이기 때문에 여기서 해야한다.
        # 이 함수에 들어왔다는 말은 사용자가 멀티케스트를 쓰겠다는 뜻이므로, 변수로 받는 부분도 좋을 것이다.
        # 현재 접속한 사용자 별로 채널이 디비등 어디에 있어야 할것이다.
        return 'hiu' + message + 'sync'

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.BROADCAST)
    async def get_message_broadcast(self, message: str) -> str:
        return 'hiu' + message + 'sync'