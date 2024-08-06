from datetime import datetime
from pydantic import BaseModel
from typing import AsyncGenerator, Optional, Any
from arbiter.service import RedisService
from arbiter.constants import (
    ArbiterMessage,
    HttpMethod,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.interface import (
    subscribe_task, 
    periodic_task, 
    http_task, 
    stream_task,
    task
)


class TestModel(BaseModel):
    name: str
    age: int
    time: datetime

class TestService(RedisService):
    
    # 이 두개를 어떻게 묶을 것인가? 시스템적으로 묶으려면,... task에 dependency를 넣어야 할 것 같다.
    # 일단 내부에서 사용하려면 이렇게 해야할 것 같다.    
    @task()
    async def return_task(self, data: Any):
        return f"{data} return_task"
    
    @http_task(method=HttpMethod.POST)
    async def task_chain(self):
        response = await self.arbiter.send_message(
            "test_service_return_task",
            ArbiterMessage(data='3434'))
        return response

    @http_task(method=HttpMethod.POST)
    async def return_constant(self):
        return "HI"
    
    @http_task(method=HttpMethod.POST)
    async def return_annotation(self) -> str:
        return "it's me"
    
    @http_task(method=HttpMethod.POST)
    async def return_pydantic_model(self) -> list[TestModel]:
        return TestModel(name="test", age=34, time=datetime.now())

    # @http_task(method=HttpMethod.POST)
    # async def return_pydantic_model_no_return_annotation(self, model: TestModel):
    #     return TestModel(name="test", age=model.age, time=datetime.now())

    # @http_task(method=HttpMethod.POST)
    # async def pydantic_param(self, message: TestModel):
    #     # await asyncio.sleep(10)
    #     return [message]
        # return TestModel(name="test", age=10, time=datetime.now())
    
    # @http_task(method=HttpMethod.POST)
    # async def get_message(self, message: list[TestModel], member: list[int]) -> list[TestModel]:
    #     # await asyncio.sleep(10)
    #     return message[0]
    
    # @stream_task(
    #     connection=StreamMethod.WEBSOCKET,
    #     communication_type=StreamCommunicationType.ASYNC_UNICAST)
    # async def on_stream(self, message: str) -> AsyncGenerator[str, None]:
    #     yield message

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.SYNC_UNICAST)
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
    async def world(self, message: str, user_id: Optional[str]) -> str:
        return message
        
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