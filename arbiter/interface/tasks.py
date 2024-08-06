import re
import inspect
import pickle
import ast
import inspect
import json
import functools
import warnings
from typing import Any, get_origin, get_args, List, Callable, AsyncGenerator
from pydantic import BaseModel
from arbiter.constants.messages import ArbiterMessage
from arbiter.utils import to_snake_case, parse_request_body
from arbiter.constants.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType,
)
from arbiter.constants import (
    ALLOWED_TYPES
)
from arbiter import Arbiter

class BaseTask:
    """
        task 들의 기본적인 속성이 무엇일까?
        retry policy? retry count?
        cold start? cold period?
    """
    def __init__(
        self,
        name: str = None,  
        routing: bool = False,
        raw_message: bool = False,
        cold_start: bool = False,
        retry_count: int = 0,
        activate_period: int = 0,
    ):
        self.name = name
        self.raw_message = raw_message
        self.cold_start = cold_start
        self.retry_count = retry_count
        self.routing = routing
        self.activate_period = activate_period
        self.has_response = True
        self.task_params = None
        self.response_type = None
    
    def __call__(self, func: Callable) -> dict[str, inspect.Parameter]:

        setattr(func, 'is_task_function', True)
                        
        task_params = {}
        signature = inspect.signature(func)
        for param in signature.parameters.values():
            if param.name == 'self':
                continue
            if param.name in task_params:
                raise ValueError(f"Duplicate parameter name: {param.name}")
            # if not isinstance(param.annotation, type):
            #     print(param.annotation)
            #     # param.annotation = get_type_hints(func).get(param.name, None)
            
            if param.annotation is None:
                warnings.warn(
                    f"Highly recommand , Parameter {param.name} should have a type annotation")

            task_params[param.name] = param
        
        # 반환 유형 힌트 가져오기
        return_annotation = signature.return_annotation
        if return_annotation != inspect.Signature.empty:
            # 반환 유형이 AsyncGenerator인지 확인하고 항목 유형 추출
            if hasattr(return_annotation, '__origin__') and return_annotation.__origin__ is AsyncGenerator:
                response_type = return_annotation.__args__[0]
            else:
                response_type = return_annotation

            origin = get_origin(response_type)
            origin_type = response_type
            if origin is list or origin is List:
                params = get_args(return_annotation)
                if len(params) != 1:
                    raise ValueError(
                        f"Invalid return type: {return_annotation}, expected: list[Type]")
                origin_type = params[0]
            if not (issubclass(origin_type, BaseModel) or origin_type in ALLOWED_TYPES):
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
            
        self.task_params = task_params        
        for attribute, value in self.__dict__.items():
            setattr(func, attribute, value)

    def parse_data(self, data: Any) -> dict[str, Any] | Any:
        """
            사용자로부터 들어오는 데이터와 함수에 선언된 파라미터를 비교한다.
            현재 json 
        """
        params = {}
        if not self.task_params:
            if isinstance(data, dict) and len(data) > 0:
                warnings.warn(
                    f"function has no parameters, but data is not empty: {data}"
                )
            return params
        try:
            data: dict[str, Any] = json.loads(data)
            """
                사용자로 부터 받은 데이터를 request_params에 맞게 파싱한다.
            """
            params = parse_request_body(data, self.task_params)
        except (json.JSONDecodeError, TypeError):
            # if len(self.task_params) != 1:
                # 이렇게되면, 첫번째 파라미터에만 데이터가 들어가게 된다.
            param_name = list(self.task_params.keys())[0]
            params = parse_request_body({param_name: data}, self.task_params)
        finally:
            return params

class ArbiterTask(BaseTask):
    
    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        @functools.wraps(func)
        async def wrapper(owner, *args: Any, **kwargs: Any):
            # TODO Refactor
            task_queue = f'{to_snake_case(owner.__class__.__name__)}_{func.__name__}'
            arbiter = getattr(owner, "arbiter", None)
            assert isinstance(arbiter, Arbiter)
            async for message in arbiter.listen(task_queue):
                assert isinstance(message, ArbiterMessage), f"Invalid message type: {type(message)}"
                try:
                    if getattr(func, "raw_message", False):
                        results = await func(owner, message.data)
                    else:
                        params = self.parse_data(message.data)
                        results = await func(owner, **params)
                    if not getattr(func, "has_response", False):
                        continue
                    if not message.id:
                        # 답장할주소가 없기때문에
                        continue
                    response = pickle.dumps(results)
                    if response and message.id:
                        await arbiter.push_message(
                            message.id, 
                            response)
                except Exception as e:
                    print(e, "exception in task")
        return wrapper    

class HttpTask(ArbiterTask):
    def __init__(
        self,
        method: HttpMethod,
        **kwargs,
    ):
        super().__init__(
            routing=True,
            **kwargs
        )
        self.method = method
        
class StreamTask(BaseTask):
    def __init__(
        self,
        connection: StreamMethod,
        communication_type: StreamCommunicationType,
        num_of_channels = 1,
        **kwargs,   
    ):
        super().__init__(
            routing=True,
            **kwargs
        )      
        self.connection = connection
        self.communication_type = communication_type
        self.num_of_channels = num_of_channels

    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        
        @functools.wraps(func)
        async def wrapper(owner, *args: Any, **kwargs: Any):
            task_queue = f'{to_snake_case(owner.__class__.__name__)}_{func.__name__}'
            arbiter = getattr(owner, "arbiter", None)
            assert isinstance(arbiter, Arbiter)
            async for message in arbiter.listen_bytes(task_queue):
                try:
                    target, data = pickle.loads(message)
                    kwargs = {'self': owner}
                    if data:
                        params = self.parse_data(data)
                        kwargs.update(params)
                    # task params에 따라 파싱할까..?
                    match self.communication_type:
                        case StreamCommunicationType.SYNC_UNICAST:
                            result = await func(**kwargs)
                            await arbiter.push_message(target, result)
                        case StreamCommunicationType.ASYNC_UNICAST:
                            async for result in func(**kwargs):
                                await arbiter.push_message(target, result)
                        case StreamCommunicationType.BROADCAST:
                            result = await func(**kwargs)
                            await arbiter.broadcast(target, result)
                except Exception as e:
                    print(e)
        return wrapper

class PeriodicTask(BaseTask):
    def __init__(
        self,
        period: float,
        queue: str = '',
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.period = period
        self.queue = queue

    def __call__(self, func: Callable) -> Callable:
        super().__call__(func)
        period = self.period
        queue = self.queue
        
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if queue:
                periodic_queue = queue
            else:
                periodic_queue = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            arbiter = getattr(self, "arbiter", None)
            assert isinstance(arbiter, Arbiter)
            async for messages in arbiter.periodic_listen(periodic_queue, period):
                await func(self, messages)
        return wrapper

class SubscribeTask(BaseTask):
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
        async def wrapper(owner, *args, **kwargs):
            arbiter = getattr(owner, "arbiter", None)
            assert isinstance(arbiter, Arbiter)
            async for message in arbiter.subscribe(self.channel):
                # TODO MARK 
                await func(owner, message)
        return wrapper
