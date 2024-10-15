from __future__ import annotations
import json
import nats
import time
import uuid
import inspect
import pickle
import asyncio
import redis.asyncio as aioredis
from pydantic import BaseModel
from redis.asyncio.client import PubSub
from typing import AsyncGenerator, Any, Callable, TypeVar, Optional, Type, get_args
from arbiter.configs import (
    ArbiterConfig,
    BrokerConfig,
    NatsBrokerConfig,
    RedisBrokerConfig)
from arbiter.brokers import ArbiterRedisBroker, ArbiterNatsBroker
from arbiter.models import ArbiterTaskModel
from arbiter.utils import is_optional_type, single_result_async_gen
from arbiter.exceptions import AribterEncodeError
from arbiter.constants import ASYNC_TASK_CLOSE_MESSAGE

class Arbiter:
    
    def __init__(
        self,
        arbiter_config: ArbiterConfig,
    ):        
        self.arbiter_config = arbiter_config
        self.broker_config = arbiter_config.broker_config
        
        if isinstance(self.broker_config, NatsBrokerConfig):
            self.broker: ArbiterNatsBroker = ArbiterNatsBroker(
                config=self.broker_config,
                name=self.arbiter_config.name,
                log_level=self.arbiter_config.log_level,
                log_format=self.arbiter_config.log_format
            )
        elif isinstance(self.broker_config, RedisBrokerConfig):
            self.broker: ArbiterRedisBroker = ArbiterRedisBroker(
                config=self.broker_config,
                name=self.arbiter_config.name,
                log_level=self.arbiter_config.log_level,
                log_format=self.arbiter_config.log_format
            )
        else:
            raise NotImplementedError("Not implemented broker")   

    async def connect(self):
        await self.broker.connect()

    async def disconnect(self):
        await self.broker.disconnect()

    async def async_task(
        self,
        target: str | ArbiterTaskModel,
        *args,
        **kwargs
    ) -> Any:

        """Request execution logic shared between task and stream."""
        timeout = self.arbiter_config.default_send_timeout
        retry = 0
        return_type = None
        request_data = await self.__request_packer(*args, **kwargs)
        
        while retry < self.arbiter_config.retry_attempts:
            try:
                results = await self.broker.request(target, request_data, timeout)
                # If single result, return it directly
                if return_type:
                    return await self.__results_unpacker(return_type, results)
                else:
                    return results
            except asyncio.TimeoutError:
                retry += 1
                time.sleep(self.arbiter_config.retry_interval)
                continue
            except Exception as e:
                raise e
        
        raise TimeoutError("Request timeout")
        
    async def async_stream(
        self,
        target: str | ArbiterTaskModel,
        *args,
        **kwargs
    ) -> AsyncGenerator[Any, None]:
        timeout = self.arbiter_config.default_send_timeout
        retry = 0
        return_type = None
        request_data = await self.__request_packer(*args, **kwargs)
        
        while retry < self.arbiter_config.retry_attempts:
            try:
                async for results in self.broker.stream(target, request_data, timeout):
                    if return_type:
                        yield await self.__results_unpacker(return_type, results)
                    else:
                        yield results
                break
            except asyncio.TimeoutError:
                retry += 1
                time.sleep(self.arbiter_config.retry_interval)
                continue
            except Exception as e:
                raise e
      
    async def async_broadcast(
        self,
        target: str | ArbiterTaskModel,
        *args,
        **kwargs
    ):
        request_data = await self.__request_packer(*args, **kwargs)
        await self.broker.broadcast(target, request_data) 
    
    async def emit_message(
        self,
        target: str | ArbiterTaskModel,
        *args,
        **kwargs
    ):
        request_data = await self.__request_packer(*args, **kwargs)
        await self.broker.emit(target, request_data)    
    
    async def __request_packer(
        self,
        *args, 
        **kwargs
    ) -> list | dict:
        # TODO Pass model parameter
        # validate model? not yet
        assert len(args) == 0 or len(kwargs) == 0, "currently, args and kwargs cannot be used together"
        data: list | dict = None
        if len(args) > 0:
            data = []
            for arg in args:
                # assert isinstance(arg, (str, int, float, bool)), "args must be str, int, float, bool"
                if isinstance(arg, BaseModel):
                    data.append(arg.model_dump())
                else:
                    data.append(arg)
        elif len(kwargs) > 0:
            data = {}
            for key, value in kwargs.items():
                # assert isinstance(value, (str, int, float, bool)), "args must be str, int, float, bool"
                if isinstance(value, BaseModel):
                    data[key] = value.model_dump()
                else:
                    data[key] = value
        else:
            data = []
            
        return data
    
    async def __results_unpacker(self, return_type: Any, results: Any):
        if is_optional_type(return_type):
            if results is None:
                return None
            return_type = get_args(return_type)[0]
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            results = return_type.model_validate_json(results)
        return results
        
        