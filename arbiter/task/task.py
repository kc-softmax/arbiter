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
from types import UnionType
from typing import  (
    Any,
    get_origin, 
    get_args, 
    List, 
    Callable,
    Type,
    Union, 
    Tuple
)
from pydantic import BaseModel
from arbiter.constants import (
    ASYNC_TASK_CLOSE_MESSAGE
)
from arbiter.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType,
)
from arbiter.utils import convert_data_to_annotation, get_pickled_data
from arbiter.service import ArbiterService
from arbiter import Arbiter


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
        self.func = None
        self.parameters: dict[str, inspect.Parameter] = {}
        self.return_type: Type = None
    
    def __call__(self, func: Callable) -> dict[str, inspect.Parameter]:
        self.func = func 
        setattr(func, 'is_task_function', True)
        setattr(func, 'task_name', func.__name__)
        setattr(func, 'task_type', self.__class__.__name__)
        
        signature = inspect.signature(func)
        for i, param in enumerate(signature.parameters.values()):
            # 만약 self나 app이라는 이름의 파라미터가 있다면 첫번째 파라미터인지 검사 한후, 
            if param.name in self.parameters:
                raise ValueError(f"Duplicate parameter name: {param.name}")

            if param.name == 'self':
                if i != 0:
                    raise ValueError("self parameter should be the first parameter")
                continue
            
            if param.annotation == AsyncGenerator:
                raise ValueError("AsyncGenerator is not allowed, use AsyncIterator instead")
            
            if param.annotation is ArbiterService:
                raise ValueError("if ArbiterService is used, it should be the first parameter and named 'self'")
            
                        
            if param.annotation is None:
                warnings.warn(
                    f"Highly recommand , Parameter {param.name} should have a type annotation")

            if param.annotation == Request:
                raise ValueError("fastapi Request is not allowed, use pydantic model instead")
            # if not isinstance(param.annotation, type):
            #     print(param.annotation)
            #     # param.annotation = get_type_hints(func).get(param.name, None)
            self.parameters[param.name] = param

        # 반환 유형 힌트 가져온다. 있으면 저장한다.
        return_annotation = signature.return_annotation
        if return_annotation == inspect.Signature.empty:
            # 없다면 코드에서 찾고 있으면 Any로 저장한다.
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
                        # return을 찾았기 때문에 Any로 설정한다.
                        # 하지만 우리는 hint를 쓰라는것을 권장한다.
                        self.return_type = Any  
                        warnings.warn(
                            "Return type hint is recommended for better performance")
            except IndentationError as e:
                print(f"IndentationError: {e}")
            except StopIteration:
                print("StopIteration: No function definition found in the parsed AST.")
            except Exception as e:
                print(f"Unexpected error: {e}")
        else:
            self.return_type = return_annotation
        
        for attribute, value in self.__dict__.items():
            setattr(func, attribute, value)
    
    def parse_requset(self, request: Any) -> dict[str, Any] | Any:
        """
            사용자로부터 들어오는 데이터와 함수에 선언된 파라미터를 비교한다.
            현재 json 
        """
        if not self.parameters:
            if isinstance(request, dict) and len(request) > 0:
                warnings.warn(
                    f"function has no parameters, but data is not empty: {request}"
                )
            return {}
        """
            args, kwargs로 들어온 경우만 처리한다.
        """
        
        if isinstance(request, list):
            # args type으로 들어온 경우
            without_default_params = {k: v for k, v in self.parameters.items() if v.default == inspect.Parameter.empty}
            if len(without_default_params) != len(request):
                raise ValueError("Invalid data length")
            # 순서대로 매핑하여 request_body를 만든다.
            request = {k: v for k, v in zip(without_default_params.keys(), request)}
        elif not isinstance(request, dict):
            request: dict[str, Any] = json.loads(request)
        
        assert isinstance(request, dict), "Invalid request data"
        
        """
            사용자로 부터 받은 데이터를 request_params에 맞게 파싱한다.
        """
        parsed_request = {}
        for name, parameter in self.parameters.items():
            annotation = parameter.annotation
            if name not in request:
                # 사용자로 부터 받은 request에 함수의 이름이 param_name이 없다면
                if parameter.default != inspect.Parameter.empty:
                    # 기본값이 있는 경우 기본값으로 넣는다.
                    parsed_request[name] = parameter.default
                elif (
                    get_origin(annotation) is Union or
                    isinstance(annotation, UnionType)
                ):
                    # parameter 가 optional type인지 확인한다.
                    # Union type 이지만 None이 없는 경우
                    if type(None) not in get_args(annotation):
                        raise ValueError(
                            f"Invalid parameter: {name}, {name} is required")
                    # Optional type이기 때문에 None을 넣어줘보자
                    parsed_request[name] = None
                else:
                    raise ValueError(
                        f"Invalid parameter: {name}, {name} is required")
            else:
                #사용자로 부터 받은 request에 param_name이 있다.
                parsed_request[name] = convert_data_to_annotation(
                    request.pop(name, None), annotation)
        if request:
            warnings.warn(f"Unexpected parameters: {request.keys()}")
        return parsed_request
        
    def results_packing(self, data: Any) -> Any:
        # MARK TODO Change
        if isinstance(data, BaseModel):
            packed_data = data.model_dump_json()
        else:
            packed_data = data
        return pickle.dumps(packed_data)
    
    
class ArbiterTask(BaseTask):
        
    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for message in arbiter.listen(queue):
                try:                    
                    message_id, data = get_pickled_data(message)
                    request = self.parse_requset(data)
                    results = await func(instance, **request)
                    if results is None:
                        continue
                except Exception as e:
                    print(e, "exception in task")
                    results = self.results_packing(e)
                finally:
                    packed_results = self.results_packing(results)
                    await arbiter.push_message(message_id, packed_results)
        return wrapper

class ArbiterAsyncTask(ArbiterTask):

    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for message in arbiter.listen(queue):
                try:
                    message_id, data = get_pickled_data(message)
                    request = self.parse_requset(data)
                    async for results in func(instance, **request):
                        await arbiter.push_message(message_id, self.results_packing(results))
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
        #         param for param in self.parameters.values() if param.annotation == ConnectionInfo
        #     ]
        #     if not connection_info_param:
        #         raise ValueError("ConnectionInfo paramter is required for connection_info=True")
        #     assert len(connection_info_param) == 1, "Only one ConnectionInfo is allowed"
        #     self.connection_info_param = self.parameters.pop(connection_info_param[0].name)
            
        @functools.wraps(func)
        async def wrapper(arbiter: Arbiter, queue: str, instance: ArbiterService):
            async for message in arbiter.listen(queue):
                try:
                    target, data = pickle.loads(message)
                    if data:
                        request = self.parse_requset(data)
                    else:
                        request = {}
                    # task params에 따라 파싱할까..?
                    match self.communication_type:
                        case StreamCommunicationType.SYNC_UNICAST:
                            results = self.results_packing(await func(instance, **request))
                            await arbiter.push_message(target, results)
                        case StreamCommunicationType.ASYNC_UNICAST:
                            async for results in func(instance, **request):
                                results = self.results_packing(results)
                                await arbiter.push_message(target, results)
                            await arbiter.push_message(target, ASYNC_TASK_CLOSE_MESSAGE)                        
                            # 끝났다고 안넣어줌
                        case StreamCommunicationType.BROADCAST:
                            results = self.results_packing(await func(instance, **request))
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