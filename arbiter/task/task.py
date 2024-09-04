from __future__ import annotations
import re
import pickle
import ast
import inspect
import json
import functools
import warnings
import pickle
from collections.abc import AsyncGenerator
from fastapi import Request
from types import NoneType
from typing import  Any, get_origin, get_args, List, Callable, Type
from pydantic import BaseModel
from arbiter.constants import (
    HEALTH_CHECK_RETRY,
    ARBITER_SERVICE_HEALTH_CHECK_INTERVAL,
    ARBITER_SERVICE_TIMEOUT,
    ALLOWED_TYPES,
    ASYNC_TASK_CLOSE_MESSAGE
)
from arbiter.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType,
)
from arbiter.data.models import (
    ArbiterTaskModel,
)
from arbiter.utils import get_task_queue_name, parse_request_body, get_pickled_data
from arbiter.service import ArbiterService
from arbiter import Arbiter

# consider func using protocol
class BaseTask:

    def __init__(
        self,
        queue: str = None,
        cold_start: bool = False,
        num_of_tasks: int = 1,
        retry_count: int = 0,
        activate_duration: int = 0,
    ):
        assert num_of_tasks > 0, "num_of_tasks should be greater than 0"
        self.queue = queue
        self.cold_start = cold_start
        self.retry_count = retry_count
        self.activate_duration = activate_duration
        self.num_of_tasks = num_of_tasks        
        self.params = None
        self.response_type = None
        self.has_response = True
        self.func = None
    
    def __call__(self, func: Callable) -> dict[str, inspect.Parameter]:
        self.func = func 
        setattr(func, 'is_task_function', True)
        setattr(func, 'task_name', func.__name__)
        setattr(func, 'task_type', self.__class__.__name__)
        params = {}
        signature = inspect.signature(func)
        for i, param in enumerate(signature.parameters.values()):
            # 만약 self나 app이라는 이름의 파라미터가 있다면 첫번째 파라미터인지 검사 한후, 
            if param.name == 'self':
                if i != 0:
                    raise ValueError("self parameter should be the first parameter")
                continue
            
            if param.annotation is ArbiterService:
                raise ValueError("if ArbiterService is used, it should be the first parameter and named 'self'")
            
            if param.name in params:
                raise ValueError(f"Duplicate parameter name: {param.name}")
                        
            if param.annotation is None:
                warnings.warn(
                    f"Highly recommand , Parameter {param.name} should have a type annotation")

            if param.annotation == Request:
                raise ValueError("fastapi Request is not allowed, use pydantic model instead")
            # if not isinstance(param.annotation, type):
            #     print(param.annotation)
            #     # param.annotation = get_type_hints(func).get(param.name, None)
            params[param.name] = param 
        
        # 반환 유형 힌트 가져오기
        return_annotation = signature.return_annotation
        if return_annotation != inspect.Signature.empty:
            # 반환 유형이 AsyncGenerator인지 확인하고 항목 유형 추출
            # print(get_origin(return_annotation), '3424')
            if get_origin(return_annotation) == AsyncGenerator:
                args = get_args(return_annotation)
                if len(args) > 2:
                    raise ValueError(
                        f"Invalid return type: {return_annotation}, expected: AsyncGenerator[Type, None]")
                if args[1] is not NoneType:
                    raise ValueError(
                        f"Invalid return type: {return_annotation}, expected: AsyncGenerator[Type, None]")
                response_type = args[0]
            else:
                response_type = return_annotation                
            origin = get_origin(response_type)
            origin_type = response_type
            if origin is list or origin is List:
                return_params = get_args(return_annotation)
                if len(return_params) != 1:
                    raise ValueError(
                        f"Invalid return type: {return_annotation}, expected: list[Type]")
                origin_type = return_params[0]
            if not (origin_type in ALLOWED_TYPES or issubclass(origin_type, BaseModel)):
                raise ValueError(f"Invalid response type: {response_type}, allowed types: {ALLOWED_TYPES}")
            self.response_type = response_type

        # 코드에서 return을 한번더 찾아 type을 확인한다.
        responst_type_in_code = None
        raw_source = inspect.getsource(func)
        # 함수의 소스를 적절하게 들여쓰기합니다.
        # 예: 함수의 첫 번째 줄 들여쓰기 길이를 기준으로 나머지 줄을 조정합니다.
        lines = raw_source.split('\n')
        indent = len(lines[0]) - len(lines[0].lstrip())
        stripped_source = '\n'.join(line[indent:] for line in lines)
        # 소스 코드를 AST로 파싱
        decorator_pattern = re.compile(r'^\s*@\w+\(.*?\)\s*\n', re.MULTILINE)
        source = decorator_pattern.sub('', stripped_source)
        # source = decorator_pattern.sub(lambda match: f'# {match.group(0)}', source)
        try:
            tree = ast.parse(source)
            # print("AST Dump:\n", ast.dump(tree, indent=4))
            # 함수 정의 노드를 찾습니다.
            func_node = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef))
            # print("Function Node Found:\n", ast.dump(func_node, indent=4))
            for node in ast.walk(func_node):
                if isinstance(node, ast.Return):
                    if isinstance(node.value, ast.Constant):
                        responst_type_in_code = type(node.value.value)
                    else:
                        responst_type_in_code = Any
        except IndentationError as e:
            print(f"IndentationError: {e}")
        except StopIteration:
            print("StopIteration: No function definition found in the parsed AST.")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        if responst_type_in_code and self.response_type:
            if responst_type_in_code is not Any and responst_type_in_code != self.response_type:
                raise ValueError(
                    f"Return type hint: {self.response_type} is different from the actual return type: {responst_type_in_code}")
            # raise ValueError(
            #     f"response_type is required for {func.__name__}, set response_type in decorator or add return type hint")
        if responst_type_in_code and not self.response_type:
            self.response_type = responst_type_in_code
        
        if not self.response_type:
            self.has_response = False
        # else:
        #     if self.response_type == Any:
        #         warnings.warn(
        #             f"{func.task_name} in arbiter, Highly recommand specify the return annotation")
            
        self.params = params        
        for attribute, value in self.__dict__.items():
            setattr(func, attribute, value)
    
    def pack_data(self, data: Any) -> Any:
        # MARK TODO Change
        if isinstance(data, BaseModel):
            packed_data = data.model_dump_json()
        else:
            packed_data = data
        return pickle.dumps(packed_data)

    def parse_data(self, data: Any) -> dict[str, Any] | Any:
        """
            사용자로부터 들어오는 데이터와 함수에 선언된 파라미터를 비교한다.
            현재 json 
        """
        params = {}
        if not self.params:
            if isinstance(data, dict) and len(data) > 0:
                warnings.warn(
                    f"function has no parameters, but data is not empty: {data}"
                )
            return params
        try:
            if not isinstance(data, dict):
                data: dict[str, Any] = json.loads(data)
            """
                사용자로 부터 받은 데이터를 request_params에 맞게 파싱한다.
            """
            if isinstance(data, list):
                # temphandle list of data
                # task params에 기본값을 제외한 걸 가져온다
                without_default_params = {k: v for k, v in self.params.items() if v.default == inspect.Parameter.empty}
                if len(without_default_params) != len(data):
                    raise ValueError("Invalid data length")
                # 순서대로 매핑하여 request_body를 만든다.
                data = {k: v for k, v in zip(without_default_params.keys(), data)}
            params = parse_request_body(data, self.params)
        except (json.JSONDecodeError, TypeError) as e:
            print(e)
            # if len(self.params) != 1:
                # 이렇게되면, 첫번째 파라미터에만 데이터가 들어가게 된다.
            param_name = list(self.params.keys())[0]
            params = parse_request_body({param_name: data}, self.params)
        finally:
            return params

class ArbiterTask(BaseTask):
        
    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for message in arbiter.listen(queue):
                try:                    
                    message_id, data = get_pickled_data(message)
                    params = {'self': instance}
                    params.update(self.parse_data(data))
                    results = await func(**params)
                    if not getattr(func, "has_response", False):
                        continue
                    response = self.pack_data(results)
                    await arbiter.push_message(
                        message_id, 
                        response)
                except Exception as e:
                    print(e, "exception in task")
        return wrapper

class ArbiterAsyncTask(ArbiterTask):

    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for message in arbiter.listen(queue):
                try:
                    message_id, data = get_pickled_data(message)
                    params = {'self': instance}
                    params.update(self.parse_data(data))                        
                    async for results in func(**params):
                        results = self.pack_data(results)
                        await arbiter.push_message(message_id, results)
                    await arbiter.push_message(message_id, ASYNC_TASK_CLOSE_MESSAGE)                        
                except Exception as e:
                    print(e)
        return wrapper

class ArbiterHttpTask(ArbiterTask):
    def __init__(
        self,
        method: HttpMethod,
        **kwargs,
    ):
        super().__init__(
            **kwargs
        )
        self.method = method
    
class ArbiterStreamTask(ArbiterTask):
    def __init__(
        self,
        connection: StreamMethod,
        communication_type: StreamCommunicationType,
        num_of_channels = 1,
        **kwargs,   
    ):
        super().__init__(
            **kwargs
        )
        # self.connection_info_param = None
        self.connection = connection
        self.communication_type = communication_type
        self.num_of_channels = num_of_channels

    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        # if self.connection_info:
        #     connection_info_param = [
        #         param for param in self.params.values() if param.annotation == ConnectionInfo
        #     ]
        #     if not connection_info_param:
        #         raise ValueError("ConnectionInfo paramter is required for connection_info=True")
        #     assert len(connection_info_param) == 1, "Only one ConnectionInfo is allowed"
        #     self.connection_info_param = self.params.pop(connection_info_param[0].name)
            
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for message in arbiter.listen(queue):
                try:
                    target, data = pickle.loads(message)
                    kwargs = {'self': instance} if instance else {}
                    # if self.connection_info:
                    #     connection_info = data.get('connection_info', None)
                    #     data = data.get('data', None)
                    #     kwargs.update(
                    #         {self.connection_info_param.name: ConnectionInfo(**connection_info)})
                    if data:
                        params = self.parse_data(data)
                        kwargs.update(params)
                    # task params에 따라 파싱할까..?
                    match self.communication_type:
                        case StreamCommunicationType.SYNC_UNICAST:
                            results = self.pack_data(await func(**kwargs))
                            await arbiter.push_message(target, results)
                        case StreamCommunicationType.ASYNC_UNICAST:
                            async for results in func(**kwargs):
                                results = self.pack_data(results)
                                await arbiter.push_message(target, results)
                            await arbiter.push_message(target, ASYNC_TASK_CLOSE_MESSAGE)                        
                            # 끝났다고 안넣어줌
                        case StreamCommunicationType.BROADCAST:
                            results = self.pack_data(await func(**kwargs))
                            await arbiter.broadcast(target, results)
                except Exception as e:
                    print(e)
        return wrapper

class ArbiterPeriodicTask(BaseTask):
    def __init__(
        self,
        interval: float,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.interval = interval

    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)        
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for messages in arbiter.periodic_listen(queue, self.interval):
                params = [instance, messages] if instance else [messages]
                await func(*params)
                    
        return wrapper

class ArbiterSubscribeTask(BaseTask):
    def __init__(
        self,
        channel: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.channel = channel

    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for message in arbiter.subscribe_listen(self.channel):
                params = [instance, message] if instance else [message]
                await func(*params)
        return wrapper