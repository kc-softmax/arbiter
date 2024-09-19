import asyncio
from datetime import datetime
from pydantic import BaseModel
from typing import AsyncGenerator, Optional, Any
from arbiter.service import ArbiterService

from arbiter.task import (
    http_task, 
    http_stream_task,
    stream_task,
    async_task,
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
    
class IncreaseRequsetModel(BaseModel):
    content: str
    length: int

class ResponseModel(BaseModel):
    content: str
    
class TestService(ArbiterService):
    
    @async_task(queue="test_service_return_task")
    async def return_async_task(self, data: NumOfParam) -> NumOfParam:
        return NumOfParam(
            first=data.first + data.second,
            second=data.second - data.first
        )
    
    @stream_task(queue="test_service_return_async_task")
    async def return_stream_task(self, text: str, length: int) -> AsyncGenerator[ResponseModel, None]:
        for i in range(length):
            yield ResponseModel(
                content=f"{text}-{i}"
            )
            await asyncio.sleep(0.1)
    
    @http_task(num_of_tasks=1)
    async def num_of_param(self, param: NumOfParam) -> Receive | None:
        print(param)
        return Receive(
            first=param.first,
            second='second',
            third=True,
        )
    
    @http_task()
    async def task_chain(self, number: NumOfParam) -> NumOfParam:
        response = await self.arbiter.async_task(
            target="test_service_return_task",
            data=number)
        return response

    @http_stream_task()
    async def stream_task_chain(self, data: IncreaseRequsetModel) -> AsyncGenerator[ResponseModel, None]:
        async for response in self.arbiter.async_stream_task(
            target="test_service_return_async_task",
            text=data.content,
            length=data.length
        ):
            yield response

    @http_stream_task()
    async def simple_http_stream_task(self, data: IncreaseRequsetModel) -> AsyncGenerator[ResponseModel, None]:
        for i in range(data.length):
            yield ResponseModel(
                content=f"{data.content}-{i}"
            )
            await asyncio.sleep(0.1)
        
    @http_task()
    async def return_constant(self, x: NumOfParam) -> int:
        return x.first + x.second + 5

### exception test worker ###
class TestException(ArbiterService):

    @http_task()
    async def connection_timeout(self) -> str:
        """not yet"""
        raise TaskConnectionTimeout()
        # return "connection timeout"

    @http_task()
    async def connection_exceed(self) -> str:
        """Add number of connection until limitation"""
        raise TaskConnectionExceed()
        # return "connection exceed"

    @http_task()
    async def task_timeout(self) -> str:
        """Didn't return anything during DEFAULT TIMEOUT"""
        raise TaskExecutionTimeout()
        # await asyncio.sleep(5.1)
        # return "task timeout"

    @http_task()
    async def check_error(self, error_type: str) -> str:
        """Check all of error"""
        match error_type:
            case "0": raise TaskAlreadyRegistered()
            case "1": raise TaskConnectionExceed()
            case "2": raise TaskConnectionTimeout()
            case "3": raise TaskExecutionTimeout()
            case _: raise Exception("Unknown Error")
