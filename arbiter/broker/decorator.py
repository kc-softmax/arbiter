import functools
from typing import Any, Callable, Coroutine, Type
from arbiter.constants.data import ArbiterMessage
from arbiter.broker.base import MessageBrokerInterface


def subscribe_task(channel: str):
    def decorator(func: Callable[[Any, Any], Any]):
        func.is_subscribe_decorated = True

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for message in broker.subscribe(channel):
                await func(self, message)
        return wrapper
    return decorator


def periodic_task(period: float = 1):
    """
    Decorator for task
    1. 기간 동안 메세지를 수집 한 후, 처리한다.
    """
    def decorator(func: Callable[[Any, Any], Any]):
        func.is_periodic_decorated = True

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            channel = self.__class__.__name__.lower() + '_' + func.__name__
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)
            async for messages in broker.periodic_listen(channel, period):
                try:
                    await func(self, messages)
                except Exception as e:
                    print(e)
        return wrapper
    return decorator


# timeout은 notify 하는쪽에서 설정한다.
# listen type은 무조건 return 이 있어야 한다.
def rpc_task(
    protocol: str = "http",
    max_tasks: int = 10,  # 최대 동시 처리 가능한 task 수
    response: bool = True,  # 응답을 받을지 여부 (보내는 쪽에서 결정할지 받는쪽에서 결정할지 선택)
):
    def decorator(func: Callable[[Any, Any], Any]):
        func.is_rpc_decorated = True

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # class name to snake case
            channel = self.__class__.__name__.lower() + '_' + func.__name__
            broker = getattr(self, "broker", None)
            assert isinstance(broker, MessageBrokerInterface)

            async for message in broker.listen(channel):
                try:
                    decoded_message = ArbiterMessage.decode(message)
                    results = await func(self, decoded_message.data)
                    response and await broker.notify(decoded_message.id, results)
                except Exception as e:
                    print(e)
        return wrapper
    return decorator
