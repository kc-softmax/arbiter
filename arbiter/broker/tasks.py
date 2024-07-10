import pickle
from typing import Any
import functools
import asyncio
from arbiter.constants.data import ArbiterMessage
from arbiter.broker.base import MessageBrokerInterface
from arbiter.utils import to_snake_case
from arbiter.constants.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType,
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
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            channel = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for message in broker.listen(channel):
                try:
                    decoded_message = ArbiterMessage.decode(message)
                    data = pickle.loads(decoded_message.data)
                    match func.communication_type:
                        case StreamCommunicationType.SYNC_UNICAST:
                            result = await func(self, *data.values())
                            await broker.push_message(
                                decoded_message.id, result)
                        case StreamCommunicationType.ASYNC_UNICAST:
                            async for result in func(self, *data.values()):
                                await broker.push_message(
                                    decoded_message.id, result)
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
        auth: bool = False,
    ):
        self.auth = auth
        self.method = method
        self.routing = True

    def __call__(self, func: HttpTaskProtocol) -> HttpTaskProtocol:
        super().__call__(func)
        @functools.wraps(func)
        async def wrapper(self, *args: Any, **kwargs: Any):
            channel = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for message in broker.listen(channel):
                try:
                    decoded_message = ArbiterMessage.decode(message)
                    request_params = pickle.loads(decoded_message.data)
                    results = await func(self, **request_params)
                    decoded_message.id and await broker.push_message(decoded_message.id, results)
                except Exception as e:
                    print(e)
        return wrapper


class PeriodicTask(Task):
    def __init__(
        self,
        period: float,
    ):
        self.period = period

    def __call__(self, func: PeriodicTaskProtocol) -> PeriodicTaskProtocol:
        super().__call__(func)
        period = self.period

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            channel = f'{to_snake_case(self.__class__.__name__)}_{func.__name__}'
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for messages in broker.periodic_listen(channel, period):
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
                await func(self, message)
        return wrapper
