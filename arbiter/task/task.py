from __future__ import annotations
import asyncio
import contextlib
import re
import pickle
import ast
import inspect
import json
import functools
import warnings
import pickle
from fastapi import Request
from collections.abc import AsyncGenerator
from types import UnionType
from typing import  (
    Any,
    AsyncIterator,
    get_origin, 
    get_args, 
    Callable,
    Type,
    Union,
    Dict
)
from pydantic import BaseModel
from arbiter.constants import (
    ASYNC_TASK_CLOSE_MESSAGE
)
from arbiter.enums import NodeState
from arbiter.utils import convert_data_to_annotation, get_pickled_data
from arbiter.data.models import ArbiterTaskNode
from arbiter.service import ArbiterService
from arbiter import Arbiter

class ArbiterAsyncTask:

    def __init__(
        self,
        queue: str = None,
        num_of_tasks: int = 1,
    ):
        assert num_of_tasks > 0, "num_of_tasks should be greater than 0"
        self.stream = False
        self.queue = queue
        self.num_of_tasks = num_of_tasks
        self.parameters: dict[str, inspect.Parameter] = {}
        self.return_type: Type = None
        self.message_queue = asyncio.Queue()

    def __results_packing(self, data: Any) -> Any:
        # MARK TODO Change
        if isinstance(data, BaseModel):
            packed_data = data.model_dump_json()
        else:
            packed_data = data
        return pickle.dumps(packed_data)

    def __single_result_async_gen(self, func_result: Any) -> AsyncIterator:
        """
        Wrap a single awaitable result into an asynchronous generator.
        """
        async def generator():
            result = await func_result
            yield result
        return generator()
    
    def _set_parameters(self, signature: inspect.Signature):
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
            
            if param.name == 'request':
                if not hasattr(self, 'request'):
                    raise ValueError("request parameter is not allowed, except request=True in decorator")
                # check request annotat
                # annotation is dict
                if param.annotation == dict:
                    continue
                origin = get_origin(param.annotation)
                if origin is dict or origin is Dict:
                    continue
                raise ValueError("request parameter should be dict")                
            
            # if not isinstance(param.annotation, type):
            #     print(param.annotation)
            #     # param.annotation = get_type_hints(func).get(param.name, None)
            self.parameters[param.name] = param
    
    def _set_return_type(self, signature: inspect.Signature, func: Callable):
        # 반환 유형 힌트 가져온다. 있으면 저장한다.
        return_annotation = signature.return_annotation
        in_function_return = False
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
            # 함수 정의 노드를 찾습니다.
            func_node = next(
                node for node in tree.body if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)))                # print("Function Node Found:\n", ast.dump(func_node, indent=4))
            for node in ast.walk(func_node):
                if isinstance(node, (ast.Yield, ast.YieldFrom)):
                    self.stream = True
                if isinstance(node, ast.Return):
                    # return을 찾았기 때문에 Any로 설정한다.
                    # 하지만 우리는 hint를 쓰라는것을 권장한다.
                    in_function_return = True
                    # warnings.warn(
                    #     "Return type hint is recommended for better performance")
                
        except IndentationError as e:
            print(f"IndentationError: {e}")
        except StopIteration:
            print("StopIteration: No function definition found in the parsed AST.")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        if return_annotation == inspect.Signature.empty:
            if in_function_return:
                self.return_type = Any
        else:
            self.return_type = return_annotation

    def _get_message_func(
        self,
        arbiter: Arbiter,
        queue: str
    ) -> AsyncGenerator[Any, None]:
        """
        Protected method that returns an asynchronous iterable from arbiter.listen.

        :param arbiter: The arbiter instance to listen with.
        :param queue: The name of the queue to listen to.
        :return: An asynchronous generator yielding messages.
        """
        return arbiter.listen(queue)
   
    def _parse_requset(self, request: Any) -> dict[str, Any] | Any:
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
        if request is None:
            # default value로 return
            for param in self.parameters.values():
                if param.default == inspect.Parameter.empty:
                    warnings.warn(f"Missing parameter: {param.name}")                    
            return {k: v.default for k, v in self.parameters.items()}
        
        if isinstance(request, list):
            # args type으로 들어온 경우
            without_default_params = {k: v for k, v in self.parameters.items() if v.default == inspect.Parameter.empty}
            if len(without_default_params) > len(request):
                raise ValueError("Invalid data length")
            # 순서대로 매핑하여 request_body를 만든다.
            request = {k: v for k, v in zip( self.parameters.keys(), request)}
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
    
    def _parse_message(self, message: Any) -> tuple[str, Any]:
        return get_pickled_data(message)
    
    def __call__(self, func: Callable) -> dict[str, inspect.Parameter]:
        setattr(func, 'is_task_function', True)
        setattr(func, 'task_name', func.__name__)
        self.func = func
        
        signature = inspect.signature(func)

        self._set_parameters(signature)
        
        self._set_return_type(signature, func)
        
        for attribute, value in self.__dict__.items():
            setattr(func, attribute, value)

        @functools.wraps(func)
        async def wrapper(
            arbiter: Arbiter,
            queue: str,
            instance: ArbiterService,
            task_node: ArbiterTaskNode
        ):

            task_node.state = NodeState.PENDING
            await arbiter.save_data(task_node)
            
            async for message in self._get_message_func(arbiter, queue):
                task_node.state = NodeState.WORKING
                await arbiter.save_data(task_node)
                is_async_gen = False
                try:
                    message_id, data = self._parse_message(message)
                    request = self._parse_requset(data)
                    func_result = func(instance, **request)
                    # Determine if func_result is an async generator
                    is_async_gen = inspect.isasyncgen(func_result)
                    if is_async_gen:
                        async_iterator = func_result
                    else:
                        # Wrap single awaitable result into an async generator
                        async_iterator = self.__single_result_async_gen(func_result)
                    async for results in async_iterator:
                        if message_id is None:
                            continue
                        packed_results = self.__results_packing(results)
                        await arbiter.push_message(message_id, packed_results)
                                                                
                except Exception as e:
                    if message_id is None:
                        print(func.__name__, message, e)
                    else:
                        await arbiter.push_message(message_id, self.__results_packing(e))
                finally:
                    if is_async_gen and message_id is not None:
                        await arbiter.push_message(message_id, ASYNC_TASK_CLOSE_MESSAGE)
                    task_node.state = NodeState.PENDING
                    await arbiter.save_data(task_node)
        return wrapper 
  
class ArbiterHttpTask(ArbiterAsyncTask):
    
    def __init__(
        self,
        request: bool = False,
        file: bool = False,
        **kwargs,
    ):
        self.http = True
        self.file = file
        self.request = request
        super().__init__(
            **kwargs
        )
    
    # def _set_return_type(self, signature: inspect.Signature, func: Callable[..., Any]):
    #     super()._set_return_type(signature, func)
    #     if self.file and self.return_type != bytes:
    #         # byte or None or Optional[bytes]
    #         raise ValueError("return type should be bytes for file=True")
    
    def _parse_requset(self, request: dict | Any) -> dict[str, Any] | Any:
        requset_data = {}
        if self.request:
            requset_data.update({
                'request': request.pop('request', {})
                })
            
        requset_data.update(
            super()._parse_requset(request))
        return requset_data

class ArbiterPeriodicTask(ArbiterAsyncTask):
    """
        periodc task는 주기적으로 실행되는 task이다.
        따라서 return type이 없다.
        또한 paramter는 무조건 list type이며, 1개이다,
        또한 기본값은 [] 이다.
    """
    def __init__(
        self,
        interval: float,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.interval = interval

    def _set_return_type(self, signature: inspect.Signature, func: Callable[..., Any]):
        super()._set_return_type(signature, func)
        assert self.return_type == None, "Periodic task should not have return type"

    def _set_parameters(self, signature: inspect.Signature):
        super()._set_parameters(signature)
        assert len(self.parameters) < 2, "Periodic task should have less than one parameter"        
        for param in self.parameters.values():
            assert get_origin(param.annotation) is list, "Periodic task parameter should be list type"
            assert param.default == [], "Periodic task parameter should have default value []"

    def _parse_message(self, message: Any) -> tuple[str, Any]:
        parsed_message = get_pickled_data(message)        
        return None, parsed_message

    def _get_message_func(
        self,
        arbiter: Arbiter,
        queue: str
    ) -> AsyncGenerator[Any, None]:
        """
        Protected method that returns an asynchronous iterable from arbiter.listen.

        :param arbiter: The arbiter instance to listen with.
        :param queue: The name of the queue to listen to.
        :return: An asynchronous generator yielding messages.
        """
        return arbiter.periodic_listen(queue, self.interval)

class ArbiterSubscribeTask(ArbiterAsyncTask):
    """
        Subscribe task는 특정 채널에 대한 메세지를 구독하는 task이다.
        따라서 return type이 없다.
    """
    def __init__(
        self,
        channel: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.channel = channel

    # def _set_return_type(self, signature: inspect.Signature, func: Callable[..., Any]):
    #     super()._set_return_type(signature, func)
    #     assert self.return_type == None, "Subscribe task should not have return type"

    def _get_message_func(
        self,
        arbiter: Arbiter,
        queue: str
    ) -> AsyncGenerator[Any, None]:
        """
        Protected method that returns an asynchronous iterable from arbiter.listen.

        :param arbiter: The arbiter instance to listen with.
        :param queue: The name of the queue to listen to.
        :return: An asynchronous generator yielding messages.
        """
        return arbiter.subscribe_listen(self.channel)