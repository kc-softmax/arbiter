import asyncio
from datetime import datetime
from pydantic import BaseModel
from typing import AsyncGenerator, Optional, Any
from arbiter.service import ArbiterService
from arbiter.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.task import (
    subscribe_task, 
    periodic_task, 
    http_task, 
    stream_task,
    async_task,
    task
)
from arbiter.exceptions import (
    TaskConnectionExceed,
    TaskConnectionTimeout,
    TaskExecutionTimeout,
    TaskAlreadyRegistered
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


class TestService(ArbiterService):
    
    # input과 output을 모두 검사
    @http_task(method=HttpMethod.POST, queue="num_of_params", num_of_tasks=1)
    async def num_of_param(self, param: NumOfParam) -> Receive | None:
        return Receive(
            first=param.first,
            second='second',
            third=True,
        )

    @http_task(method=HttpMethod.POST)
    async def single_params(self, token: str) -> str:
        return token + 'single_params'

    @http_task(method=HttpMethod.POST)
    async def two_params(self, user_id: int, item_id: int | None) -> Receive | None:
        return Receive(
            first=1,
            second='second',
            third=True,
        )

    @http_task(method=HttpMethod.POST)
    async def list_params(self, user_ids: list[int], item_ids: list[NumOfParam]) -> Receive | None:
        return Receive(
            first=1,
            second='second',
            third=True,
        )

    @http_task(method=HttpMethod.POST, queue="type_of_params_HEEE")
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
    @task(queue="test_service_return_task")
    async def return_task(self, data: int) -> Receive:
        return Receive(
            first=data,
            second='1',
            third=True,
        )
    
    @async_task(queue="test_service_return_async_task")
    async def return_async_task(self, data: str, item_id: int) -> AsyncGenerator[str, None]:
        for i in range(3):
            yield f"{data} return_async_task qwer qwer {i}, {item_id}"
            await asyncio.sleep(0.1)
    
    @http_task(method=HttpMethod.POST)
    async def task_chain(self):
        response = await self.arbiter.async_task(
            target="test_service_return_task",
            data='3434')
        return response

    @http_task(method=HttpMethod.POST)
    async def async_task_chain(self):
        async for response in self.arbiter.async_stream_task(
            target="test_service_return_async_task",
            data='3434',
            item_id=3
        ):
            print(response)

    @http_task(method=HttpMethod.POST)
    async def return_constant(self):
        x = 4
        return x
    
    @http_task(method=HttpMethod.POST)
    async def return_annotation(self) -> str:
        return "it's me"
    
    @http_task(method=HttpMethod.POST)
    async def return_pydantic_model(self) -> list[TestModel | None]:
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

    @periodic_task(interval=5)  # TODO optioanlq
    async def hello_world(self, messages: list[bytes]):
        pass
        # print(f"hello_world: {messages}")


### exception test worker ###
class TestException(ArbiterService):

    @http_task(method=HttpMethod.POST)
    async def connection_timeout(self) -> str:
        """not yet"""
        raise TaskConnectionTimeout()
        # return "connection timeout"

    @http_task(method=HttpMethod.POST)
    async def connection_exceed(self) -> str:
        """Add number of connection until limitation"""
        raise TaskConnectionExceed()
        # return "connection exceed"

    @http_task(method=HttpMethod.POST)
    async def task_timeout(self) -> str:
        """Didn't return anything during DEFAULT TIMEOUT"""
        raise TaskExecutionTimeout()
        # await asyncio.sleep(5.1)
        # return "task timeout"

    @http_task(method=HttpMethod.POST)
    async def check_error(self, error_type: str) -> str:
        """Check all of error"""
        match error_type:
            case "0": raise TaskAlreadyRegistered()
            case "1": raise TaskConnectionExceed()
            case "2": raise TaskConnectionTimeout()
            case "3": raise TaskExecutionTimeout()
            case _: raise Exception("Unknown Error")