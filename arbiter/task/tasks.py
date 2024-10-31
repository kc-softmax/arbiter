from __future__ import annotations
import copy
import asyncio
import contextlib
import multiprocessing
import re
import pickle
import ast
import inspect
import json
import functools
import time
import warnings
import pickle
from fastapi import Request
from collections.abc import AsyncGenerator
from multiprocessing.synchronize import Event as EventType
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
from arbiter.configs import ArbiterConfig
from arbiter.constants import (
    ASYNC_TASK_CLOSE_MESSAGE
)
from arbiter.enums import NodeState
from arbiter.utils import (
    transform_type_from_annotation,
    convert_data_to_annotation,
    single_result_async_gen,
    get_pickled_data
)
from arbiter.data.models import ArbiterTaskNode
from arbiter.task.task_runner import AribterTaskNodeRunner
from arbiter import Arbiter

class ArbiterAsyncTask(AribterTaskNodeRunner):

    def __init__(
        self,
        *,
        queue: str = None,
        num_of_tasks: int = 1,
        timeout: float = 10,
        retries: int = 3,
        retry_delay: float = 1,
        strict_mode: bool = True,
        log_level: str | None = None,
        log_format: str | None = None
    ):
        super().__init__()
        assert num_of_tasks > 0, "num_of_tasks should be greater than 0"
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.log_level = log_level
        self.log_format = log_format
        self.strict_mode = strict_mode
        self.queue = queue
        self.num_of_tasks = num_of_tasks
        self.stream = False
        self.node = ArbiterTaskNode(state=NodeState.INACTIVE)

        self.func: Callable = None        
        self.parameters: dict[str, inspect.Parameter] = None
        self.arbiter_parameter: tuple[str, Arbiter] = None

    def setup_task_node(self, func: Callable):
        setattr(func, 'is_task_function', True)
        if self.queue is None:
            self.queue = func.__name__
        signature = inspect.signature(func)
        parameters, arbiter_parameter = self._check_parameters(signature)
        return_type = self._check_return_type(signature, func)
        transformed_parameters = self._transform_parameters(parameters)
        transformed_return_type = self._transform_return_type(return_type)
        
        assert self.node and isinstance(self.node, ArbiterTaskNode), "Invalid node"
        self.node.name = func.__name__
        self.node.queue = self.queue
        self.node.transformed_parameters = json.dumps(transformed_parameters)
        self.node.transformed_return_type = json.dumps(transformed_return_type)
        self.node.timeout = self.timeout
        self.parameters = parameters
        self.arbiter_parameter = arbiter_parameter
        self.func = func
                
    def _check_parameters(
        self,
        signature: inspect.Signature
    ) -> tuple[dict[str, inspect.Parameter], tuple[str, Arbiter]]:
        parameters: dict[str, inspect.Parameter] = {}
        arbiter_parameter = None
        for i, param in enumerate(signature.parameters.values()):
            # 만약 self나 app이라는 이름의 파라미터가 있다면 첫번째 파라미터인지 검사 한후, 
            if param.name in parameters:
                raise ValueError(f"Duplicate parameter name: {param.name}")
            if param.annotation == Arbiter:
                arbiter_parameter = (param.name, param.annotation)
                continue
            
            if param.annotation == AsyncGenerator:
                raise ValueError("AsyncGenerator is not allowed, use AsyncIterator instead")            
                        
            if param.annotation is None:
                warnings.warn(
                    f"Highly recommand , Parameter {param.name} should have a type annotation")

            if param.annotation == Request:
                raise ValueError("fastapi Request is not allowed, use pydantic model instead")
                        
            parameters[param.name] = param
        return parameters, arbiter_parameter
    
    def _check_return_type(self, signature: inspect.Signature, func: Callable) -> Type:
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
                return Any
        else:
            return return_annotation

    def _get_message_func(
        self,
        arbiter: Arbiter,
    ) -> AsyncGenerator[Any, None]:
        """
        Protected method that returns an asynchronous iterable from arbiter.listen.

        :param arbiter: The arbiter instance to listen with.
        :param queue: The name of the queue to listen to.
        :return: An asynchronous generator yielding messages.
        """
        return arbiter.broker.listen(self.queue)
 
    def _results_packing(self, data: Any) -> Any:
        # MARK TODO Change
        if isinstance(data, BaseModel):
            packed_data = data.model_dump_json()
        else:
            packed_data = data
        return pickle.dumps(packed_data)
   
    def _parse_requset(
        self,
        request: Any,
    ) -> dict[str, Any] | Any:
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
    
    def _transform_parameters(self, parameters: dict[str, inspect.Parameter]) -> dict[str, list]:
        transformed_parameters: dict[str, list] = {}
        for name, parameter in parameters.items():
            assert name not in transformed_parameters, "Duplicate parameter name"
            assert isinstance(parameter, inspect.Parameter), f"{name} is not a parameter"
            annotation = parameter.annotation
            parameter_types = transform_type_from_annotation(annotation)
            for parameter_type in parameter_types:
                transformed_parameters[name] = []
                if issubclass(parameter_type, BaseModel):
                    transformed_parameters[name].append(parameter_type.model_json_schema())
                else:
                    transformed_parameters[name].append(parameter_type.__name__)
        return transformed_parameters    
    
    def _transform_return_type(self, return_type: Type) -> list[Any]:
        if return_type is None:
            return []
        transformed_return_type: list[Any] = []
        for return_type in transform_type_from_annotation(return_type):
            if issubclass(return_type, BaseModel):
                transformed_return_type.append(return_type.model_json_schema())
            else:
                transformed_return_type.append(return_type.__name__)
        return transformed_return_type
    
    def __call__(self, func: Callable[..., Any] = None):
        if func is None and self.func is None:
            raise ValueError("func should be provided")
        if func is not None and self.func is not None:
            raise ValueError("func should be provided only once")
        if func is not None and self.func is None:
            self.setup_task_node(func)
        # parameters = copy.deepcopy(self.parameters)
        @functools.wraps(self.func)
        async def wrapper(
            arbiter: Arbiter,
            executor: Callable = None,
        ):
            async for reply, message in self._get_message_func(arbiter):
                is_async_gen = False
                try:
                    parsed_message = self._parse_message(message)
                    request = self._parse_requset(parsed_message)
                    if self.arbiter_parameter:
                        request[self.arbiter_parameter[0]] = arbiter
                    if executor:
                        func_result = self.func(executor, **request)
                    else:
                        func_result = self.func(**request)
                    # Determine if func_result is an async generator
                    is_async_gen = inspect.isasyncgen(func_result)
                    if is_async_gen:
                        async_iterator = func_result
                    else:
                        # Wrap single awaitable result into an async generator
                        async_iterator = single_result_async_gen(func_result)
                    async for results in async_iterator:
                        if not reply:
                            continue
                        packed_results = self._results_packing(results)
                        await arbiter.broker.emit(reply, packed_results)
                        # await arbiter.push_message(message_id, packed_results)
                                                                
                except Exception as e:
                    if reply is None:
                        pass
                    else:
                        await arbiter.broker.emit(reply, self._results_packing(e))
                finally:
                    if is_async_gen and reply is not None:
                        await arbiter.broker.emit(reply, ASYNC_TASK_CLOSE_MESSAGE)
              
        return wrapper 
  
class ArbiterHttpTask(ArbiterAsyncTask):
    
    def __init__(
        self,
        request: bool = False,
        file: bool = False,
        queue: str = None,
        num_of_tasks: int = 1,
        timeout: float = 10,
        retries: int = 3,
        retry_delay: float = 1,
        strict_mode: bool = True,
        log_level: str | None = None,
        log_format: str | None = None
    ):
        super().__init__(
            queue=queue,
            num_of_tasks=num_of_tasks,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            strict_mode=strict_mode,
            log_level=log_level,
            log_format=log_format
        )
        self.file = file
        self.request = request
        
    def setup_task_node(self, func: Callable):
        super().setup_task_node(func)
        assert isinstance(self.node, ArbiterTaskNode), "Invalid node"
        self.node.http = True
        self.node.file = self.file
        self.node.request = self.request        
    
    def _parse_requset(self, request: dict | Any) -> dict[str, Any] | Any:
        requset_data = {}
        if self.request:
            requset_data.update({
                'request': request.pop('request', {})
                })
            
        requset_data.update(
            super()._parse_requset(request))
        return requset_data
    
    def _check_parameters(
        self, 
        signature: inspect.Signature
    ) -> tuple[dict[str, inspect.Parameter], tuple[str, Arbiter]]:
        parameters, arbiter_parameter = super()._check_parameters(signature)
        if self.request:
            # request parameter를 사용할 경우 검사한다.
            for param in parameters.values():
                if param.name == 'request':
                    # check request annotat
                    # annotation is dict
                    if param.annotation == dict:
                        continue
                    origin = get_origin(param.annotation)
                    if origin is dict or origin is Dict:
                        continue
                    raise ValueError("request parameter should be dict")
            
        return parameters, arbiter_parameter
    
    
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
        queue: str = None,
        num_of_tasks: int = 1,
        timeout: float = 10,
        retries: int = 3,
        retry_delay: float = 1,
        strict_mode: bool = True,
        log_level: str | None = None,
        log_format: str | None = None
    ):
        super().__init__(
            queue=queue,
            num_of_tasks=num_of_tasks,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            strict_mode=strict_mode,
            log_level=log_level,
            log_format=log_format
        )
        self.interval = interval

    # def _set_return_type(self, signature: inspect.Signature, func: Callable[..., Any]):
    #     super()._set_return_type(signature, func)
    #     warnings.warn("Periodic task should not have return type")

    def _parse_message(self, message: Any) -> tuple[str, Any]:
        assert isinstance(message, list), "Periodic task should have list type message"
        return [
            get_pickled_data(data) for data in message
        ]
    
    def _parse_requset(
        self, 
        request: Any,
    ) -> dict[str, Any] | Any:
        # TODO update this method
        def merge_dicts(*dicts):
            merged_dict = {}
            for d in dicts:
                for key, value in d.items():
                    if key in merged_dict:
                        merged_dict[key].extend(value)
                    else:
                        merged_dict[key] = value[:]
            return merged_dict
        
        parsed_request = [
            super()._parse_requset([data], self.parameters)
            for data in request
        ]    
        return merge_dicts(*parsed_request)

    def _check_parameters(
        self, 
        signature: inspect.Signature
    ) -> tuple[dict[str, inspect.Parameter], tuple[str, Arbiter]]:
        parameters, arbiter_parameter = super()._check_parameters(signature)
        assert len(parameters) < 2, "Periodic task should have less than one parameter"
        for param in parameters.values():
            assert get_origin(param.annotation) is list, "Periodic task parameter should be list type"
            assert param.default == [], "Periodic task parameter should have default value []"
        return parameters, arbiter_parameter

    def _get_message_func(
        self,
        arbiter: Arbiter,
    ) -> AsyncGenerator[Any, None]:
        """
        Protected method that returns an asynchronous iterable from arbiter.listen.

        :param arbiter: The arbiter instance to listen with.
        :param queue: The name of the queue to listen to.
        :return: An asynchronous generator yielding messages.
        """
        return arbiter.broker.periodic_listen(self.queue, self.interval)

class ArbiterSubscribeTask(ArbiterAsyncTask):
    """
        Subscribe task는 특정 채널에 대한 메세지를 구독하는 task이다.
    """

    # def _set_return_type(self, signature: inspect.Signature, func: Callable[..., Any]):
    #     super()._set_return_type(signature, func)
    #     assert self.return_type == None, "Subscribe task should not have return type"

    def _get_message_func(
        self,
        arbiter: Arbiter,
    ) -> AsyncGenerator[Any, None]:
        """
        Protected method that returns an asynchronous iterable from arbiter.listen.

        :param arbiter: The arbiter instance to listen with.
        :param queue: The name of the queue to listen to.
        :return: An asynchronous generator yielding messages.
        """
        return arbiter.broker.subscribe_listen(self.queue)