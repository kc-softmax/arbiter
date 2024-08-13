import asyncio
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
    async_task,
    task
)


class NumOfParam(BaseModel):
    first: int
    second: int


class TypeOfParam(BaseModel):
    first: bool
    second: int


class Receive(BaseModel):
    first: int
    second: str
    third: bool


class TestModel(BaseModel):
    name: str
    age: int
    time: datetime

class TestService(RedisService):
    
    # input과 output을 모두 검사
    @http_task(method=HttpMethod.POST)
    async def num_of_param(self, param: NumOfParam) -> Receive:
        return Receive(
            first=1,
            second='second',
            third=True,
        )

    @http_task(method=HttpMethod.POST)
    async def type_of_param(self, param: TypeOfParam) -> Receive:
        # 리턴값이 없을 때 지연시간이 걸린다
        return Receive(
            first=1,
            second='1',
            third=True,
        )

    @http_task(method=HttpMethod.POST)
    async def wrong_type_of_param(self, param: TypeOfParam) -> Receive:
        # 리턴값이 없을 때 지연시간이 걸린다
        # 개발자의 실수를 검사
        return Receive()

    @http_task(method=HttpMethod.POST)
    async def return_nobody(self):
        pass

    # @http_task(method=HttpMethod.POST)
    # def post_form_param_set(items: set = Form()) -> set:
    #     return items

    # @http_task(method=HttpMethod.POST)
    # def post_form_param_tuple(items: tuple = Form()) -> tuple:
    #     return items

    # get은 보류
    # @http_task(method=HttpMethod.GET)
    # async def get_query_param(self, first: int, second: str) -> int:
    #     print(type(first), type(second))
    #     return 200

    # @http_task(method=HttpMethod.GET)
    # async def get_model_param(self, first: int, second: str) -> int:
    #     print(type(first), type(second))
    #     return 200

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.BROADCAST)
    async def simple_ping_pong(self, ping: str) -> str:
        pong = 'pong'
        return pong

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.BROADCAST)
    async def type_of_text(self, ping: str) -> str:
        pong = 'pong'
        return pong


    # 이 두개를 어떻게 묶을 것인가? 시스템적으로 묶으려면,... task에 dependency를 넣어야 할 것 같다.
    # 일단 내부에서 사용하려면 이렇게 해야할 것 같다.    
    @task()
    async def return_task(self, data: Any):
        return f"{data} return_task qwer qwer"
    
    @async_task()
    async def return_async_task(self, data: Any):
        for i in range(3):
            yield f"{data} return_async_task qwer qwer {i}"
            await asyncio.sleep(1)
    
    @http_task(method=HttpMethod.POST)
    async def task_chain(self):
        response = await self.send_task(
            task_queue="test_service_return_task",
            data='3434',
            wait_response=True)
        return response

    @http_task(method=HttpMethod.POST)
    async def return_constant(self):
        return "HI"
    
    @http_task(method=HttpMethod.POST)
    async def return_annotation(self) -> str:
        return "it's me"
    
    @http_task(method=HttpMethod.POST)
    async def return_pydantic_model(self) -> list[TestModel]:
        return []

    @stream_task(
        connection=StreamMethod.WEBSOCKET,
        communication_type=StreamCommunicationType.ASYNC_UNICAST)
    async def search_company_policy(
        self,
        message: str, 
        user_id: int | None
    ) -> AsyncGenerator[str, None]:
        pass

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
        communication_type=StreamCommunicationType.ASYNC_UNICAST)
    async def stream_async_task(self, message: str) -> AsyncGenerator[str, None]:
        async for result in self.send_async_task(
            task_queue="test_service_return_async_task",
            data=message):
            yield result

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