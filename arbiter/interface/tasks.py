import inspect
import pickle
import types
import json
import functools
from typing import Any, Type, get_origin, get_args, List, Union
from pydantic import BaseModel, Field
from arbiter.constants.messages import ArbiterMessage
from arbiter.interface.base import ArbiterInterface
from arbiter.utils import to_snake_case, get_default_type_value
from arbiter.constants.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType,
)
from arbiter.constants import (
    ALLOWED_TYPE,
    AUTH_PARAMETER
)
from arbiter.constants.protocols import (
    TaskProtocol,
    HttpTaskProtocol,
    StreamTaskProtocol,
    PeriodicTaskProtocol,
    SubscribeTaskProtocol,
)
class DummyResponseModel(BaseModel):
    response: str = Field(default='success')


class Task:
    def __call__(self, func: TaskProtocol):
        func.is_task_function = True
        func.task_name = self.__class__.__name__
        for attribute, value in self.__dict__.items():
            setattr(func, attribute, value)
        return func

class StreamTask(Task):
    def __init__(
        self,
        connection: StreamMethod,
        communication_type: StreamCommunicationType,
        num_of_channels = 1,
        auth: bool = False,
    ):
        self.auth = auth
        self.connection = connection
        self.communication_type = communication_type
        self.num_of_channels = num_of_channels
        self.routing = True

    def __call__(self, func: StreamTaskProtocol) -> StreamTaskProtocol:
        super().__call__(func)
        signature = inspect.signature(func)
        message_type = None
        extra_params: dict[str, inspect.Parameter] = {}
        for i, param in enumerate(signature.parameters.values()):
            if param.name == 'self':
                continue
            if i == 1:
                if param.annotation not in [bytes, str]:
                    raise ValueError(f"Invalid parameter type: {param.annotation}, stream task only supports bytes and str")
                message_type = param
            else:
                if param.name in extra_params:
                    raise ValueError(f"Duplicate parameter name: {param.name}")
                extra_params[param.name] = param
                
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            func_queue = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            arbiter = getattr(self, "arbiter", None)
            assert isinstance(arbiter, ArbiterInterface)
            async for message in arbiter.listen_bytes(func_queue):# 이 채널은 함수의 채널 
                try:
                    target, message, info = pickle.loads(message)
                    if not message_type and not extra_params:
                        await func(self)
                        continue
                    if not isinstance(info, dict):
                        raise ValueError(f"Invalid info type: {type(info)}, info should be dict")
                    if not extra_params and info:
                        raise ValueError(f"Invalid info: {info}, info should be empty, {func.__name__} has no extra parameters")
                    kwargs = {'self': self, message_type.name: message}
                    """
                        방식 변경
                        extra_params 와 info를 검사한다.
                        - extra_params에 없는 key가 info에 있다면 에러를 발생시킨다.
                        - extra_params에 있는 key가 info에 없다면
                        -  extra_params의 default value가 있는지 확인
                        -  extra_params의 type 이 Optional인지 확인
                    """
                    for param_key, param in extra_params.items():
                        if param_key not in info:
                            if param.default != inspect.Parameter.empty:
                                kwargs[param_key] = param.default
                            elif (
                                get_origin(param.annotation) is Union or
                                isinstance(param.annotation, types.UnionType)
                            ):
                                if type(None) not in get_args(param.annotation):
                                    raise ValueError(
                                        f"Invalid parameter: {param_key}, {param_key} is required")
                                # Optional type
                                kwargs[param_key] = get_default_type_value(param)                            
                            else:
                                raise ValueError(
                                    f"Invalid parameter: {param_key}, {param_key} is required"
                                )
                        else:
                            # 검사를 해야한다?
                            kwargs[param_key] = info.pop(param_key, None)
                    if info:
                        raise ValueError(f"Invalid info: {info}, extra parameters: {extra_params.keys()}")
                    if isinstance(message, bytes) and message_type.annotation == str:
                        message = message.decode()
                    if isinstance(message, str) and message_type.annotation == bytes:
                        message = message.encode()
                    match func.communication_type:
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


class HttpTask(Task):
    def __init__(
        self,
        method: HttpMethod,
        response_model: Type[BaseModel] = None,
        auth: bool = False,
    ):
        self.auth = auth
        self.method = method
        self.response_model = response_model
        self.routing = True

    def __call__(self, func: HttpTaskProtocol) -> BaseModel | str | bytes:
        super().__call__(func)
        if not self.response_model:
            # generate dummy response model                
            self.response_model = DummyResponseModel
        func.response_model = self.response_model
        signature = inspect.signature(func)
        response_model = self.response_model
        request_models = {}
        for param in signature.parameters.values():
            if param.name == 'self':
                continue
            origin = get_origin(param.annotation)
            if origin is list or origin is List:
                request_models[param.name] = [get_args(param.annotation)[0]]
            else:
                request_models[param.name] = param.annotation

        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            channel = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            arbiter = getattr(self, "arbiter", None)
            assert isinstance(arbiter, ArbiterInterface)
            async for message in arbiter.listen(channel):
                try:
                    message: ArbiterMessage
                    try:
                        request_json = json.loads(message.data)
                    except json.JSONDecodeError:
                        request_json = {}
                    request_params = {}
                    for k, v in request_json.items():
                        if k in request_models:
                            model = request_models[k]
                            if isinstance(model, list):
                                model = model[0]
                                assert isinstance(v, list)
                                if issubclass(model, BaseModel):
                                    request_params[k] = [
                                        model.model_validate(_v)
                                        for _v in v
                                    ]
                                else:
                                    request_params[k] = v
                            else:
                                if issubclass(model, BaseModel):
                                    request_params[k] = model.model_validate(v)
                                else:
                                    request_params[k] = v
                    
                    results = await func(self, **request_params)
                    if response_model == DummyResponseModel:
                        results = DummyResponseModel(response=results)
                        
                    if isinstance(results, list):
                        new_results = []
                        for result in results:
                            if isinstance(result, BaseModel):
                                new_results.append(result.model_dump_json())
                            else:
                                new_results.append(result)
                        results = json.dumps(new_results)
                    else:
                        if isinstance(results, BaseModel):
                            results = results.model_dump_json()
                    if results and message.id:
                        await arbiter.push_message(
                            message.id, 
                            results)
                except Exception as e:
                    print(e)
        return wrapper


class PeriodicTask(Task):
    def __init__(
        self,
        period: float,
        queue: str = '',
    ):
        self.period = period
        self.queue = queue

    def __call__(self, func: PeriodicTaskProtocol) -> PeriodicTaskProtocol:
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
            assert isinstance(arbiter, ArbiterInterface)
            async for messages in arbiter.periodic_listen(periodic_queue, period):
                await func(self, messages)
        return wrapper


class SubscribeTask(Task):
    def __init__(
        self,
        channel: str,
    ):
        self.channel = channel

    def __call__(self, func: SubscribeTaskProtocol) -> SubscribeTaskProtocol:
        super().__call__(func)
        channel = self.channel
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            arbiter = getattr(self, "arbiter", None)
            assert isinstance(arbiter, ArbiterInterface)
            async for message in arbiter.subscribe(channel):
                # TODO MARK 
                await func(self, message)
        return wrapper
