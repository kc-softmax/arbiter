import inspect
import pickle
import json
import uuid
import functools
from typing import Any, Type
from pydantic import BaseModel
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


class Task:
    def __call__(self, func: TaskProtocol):
        func.is_task_function = True
        for attribute, value in self.__dict__.items():
            setattr(func, attribute, value)
        return func

class StreamTask(Task):
    def __init__(
        self,
        connection: StreamMethod,
        communication_type: StreamCommunicationType,
        auth: bool = False,
    ):
        self.auth = auth
        self.connection = connection
        self.communication_type = communication_type
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
                raise ValueError("Stream task only supports one parameter")
            request_type = param.annotation
        
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            channel = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)

            # response_queue
            async for message in broker.listen_bytes(channel):
                try:
                    response_queue, receive_data = pickle.loads(message)
                    if isinstance(receive_data, bytes) and request_type == str:
                        receive_data = receive_data.decode()
                    if isinstance(receive_data, str) and request_type == bytes:
                        receive_data = receive_data.encode()
                    match func.communication_type:
                        case StreamCommunicationType.SYNC_UNICAST:
                            result = await func(self, receive_data)
                            await broker.push_message(
                                response_queue, result)
                        case StreamCommunicationType.ASYNC_UNICAST:
                            async for result in func(self, receive_data):
                                await broker.push_message(
                                    response_queue, result)
                    # results = await func(self, decoded_message.data)
                    # await broker.push_message(
                    #     decoded_message.id, results)
                    # print("StreamTask")
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
        func.response_model = self.response_model
        signature = inspect.signature(func)
        request_models = {}
        for param in signature.parameters.values():
            if param.name == 'self':
                continue
            request_models[param.name] = param.annotation
        
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            channel = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for message in broker.listen(channel):
                try:
                    request_json = json.loads(message.data)
                    request_params = {}
                    for k, v in request_json.items():
                        if k in request_models:
                            model = request_models[k]
                            if issubclass(model, BaseModel):
                                request_params[k] = model.model_validate(v)
                            else:
                                request_params[k] = v
                    results = await func(self, **request_params)
                    if isinstance(results, BaseModel):
                        results = results.model_dump_json()
                    message.id and await broker.push_message(
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
                try:
                    await func(self, messages)
                except Exception as e:
                    print(e)
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
