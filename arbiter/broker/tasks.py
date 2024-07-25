import inspect
import pickle
import json
import functools
from typing import Any, Type, get_origin, get_args, List
from pydantic import BaseModel, Field
from arbiter.constants.messages import ArbiterMessage
from arbiter.broker.base import MessageBrokerInterface
from arbiter.utils import to_snake_case
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
        request_type = None
        for param in signature.parameters.values():
            if param.name == 'self':
                continue
            if param.annotation not in [bytes, str]:
                raise ValueError(f"Invalid parameter type: {param.annotation}, stream task only supports bytes and str")
            if request_type:
                continue
                # raise ValueError("Stream task only supports one parameter")
            request_type = param.annotation
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            func_queue = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for message in broker.listen_bytes(func_queue):# 이 채널은 함수의 채널 
                try:
                    target, receive_data = pickle.loads(message)
                    if isinstance(receive_data, bytes) and request_type == str:
                        receive_data = receive_data.decode()
                    if isinstance(receive_data, str) and request_type == bytes:
                        receive_data = receive_data.encode()
                    match func.communication_type:
                        case StreamCommunicationType.SYNC_UNICAST:
                            result = await func(self, receive_data)
                            await broker.push_message(target, result)
                        case StreamCommunicationType.ASYNC_UNICAST:
                            async for result in func(self, receive_data):
                                await broker.push_message(target, result)
                        case StreamCommunicationType.BROADCAST:
                            result = await func(self, receive_data)
                            await broker.broadcast(target, result)
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
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for message in broker.listen(channel):
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
                        await broker.push_message(
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
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for messages in broker.periodic_listen(periodic_queue, period):
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
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for message in broker.subscribe(channel):
                # TODO MARK 
                await func(self, message)
        return wrapper
