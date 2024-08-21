import inspect
import functools

from typing import Callable
from fastapi import FastAPI
from arbiter.interface import (
    http_task,
    stream_task
)


class function_wrapper(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __call__(self, *args, **kwargs):
        return self.wrapped(*args, **kwargs)


class Arbiter(FastAPI):
    def __init__(self) -> None:
        super().__init__()

    @function_wrapper
    def http_task(self, func, **kwargs):
        def decorator(func):
            async def wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                return result
            return wrapper
        return decorator

    def stream_task(self, connection, communication_type):
        def decorator(func):
            async def wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                return result
            return wrapper
        return decorator


# arbiter = Arbiter()
