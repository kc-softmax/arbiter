from __future__ import annotations
import time
import uuid
import asyncio
from pydantic import BaseModel
from typing import AsyncGenerator, Any, get_args
from arbiter.configs import (
    ArbiterConfig,
    NatsArbiterConfig,
    RedisArbiterConfig
)
from arbiter.brokers import ArbiterRedisBroker, ArbiterNatsBroker
from arbiter.models import ArbiterTaskModel
from arbiter.utils import is_optional_type

class Arbiter:
    
    def __init__(
        self,
        arbiter_config: ArbiterConfig,
    ):
        if isinstance(arbiter_config, NatsArbiterConfig):
            self.broker: ArbiterNatsBroker = ArbiterNatsBroker(
                host=arbiter_config.host,
                port=arbiter_config.port,
                user=arbiter_config.user,
                password=arbiter_config.password,
                max_reconnect_attempts=arbiter_config.max_reconnect_attempts,
                name=arbiter_config.name,
                log_level=arbiter_config.log_level,
                log_format=arbiter_config.log_format)
        elif isinstance(arbiter_config, RedisArbiterConfig):
            assert False, "Not implemented broker"
            # self.broker: ArbiterRedisBroker = ArbiterRedisBroker(
            #     config=self.broker_config,
            #     name=arbiter_config.name,
            #     log_level=arbiter_config.log_level,
            #     log_format=arbiter_config.log_format)
        else:
            raise NotImplementedError("Not implemented broker")   
        self.arbiter_config = arbiter_config
        self.headers: dict[str, Any] = None        

    @property
    def name(self) -> str:
        return self.arbiter_config.name

    def set_headers(self, headers: dict[str, Any]):
        self.headers = headers
    
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
        timeout = kwargs.pop("timeout", self.arbiter_config.default_send_timeout)
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
                print("Timeout in request")
                retry += 1
                time.sleep(self.arbiter_config.retry_interval)
                continue
            except Exception as e:
                print("Error in request", e)
                raise e
        
        raise TimeoutError("Request timeout")
        
    async def async_stream(
        self,
        target: str | ArbiterTaskModel,
        *args,
        **kwargs
    ) -> AsyncGenerator[Any, None]:
        timeout = kwargs.pop("timeout", self.arbiter_config.default_send_timeout)
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
        # check type validation?
        await self.broker.emit(target, request_data)    
    
    async def __request_packer(
        self,
        *args, 
        **kwargs
    ) -> list | dict:
        # TODO Pass model parameter
        # validate model? not yet
        assert len(args) == 0 or len(kwargs) == 0, "currently, args and kwargs cannot be used together"
        
        # 주입식 headers 검사
        if "headers" in kwargs:
            headers = kwargs.pop("headers")

            if "traceparent" in headers:
                raise ValueError("traceparent is reserved keyword")
            
            if self.headers:
                self.headers.update(headers)
            else:
                self.headers = headers          

        # TODO short-circuiting
        if self.headers:
            headers = self.headers
            self.headers = None
        else:
            headers = {"traceparent": str(uuid.uuid4())}
            
        data: list | dict = None
        if len(args) > 0:
            data = [headers]
            for arg in args:
                # assert isinstance(arg, (str, int, float, bool)), "args must be str, int, float, bool"
                if isinstance(arg, BaseModel):
                    data.append(arg.model_dump())
                else:
                    data.append(arg)
            return data
        elif len(kwargs) > 0:
            data = {'__header__': headers}
            for key, value in kwargs.items():
                # assert isinstance(value, (str, int, float, bool)), "args must be str, int, float, bool"
                if isinstance(value, BaseModel):
                    data[key] = value.model_dump()
                else:
                    data[key] = value
            return data
            
        return [headers]
    
    async def __results_unpacker(self, return_type: Any, results: Any):
        if is_optional_type(return_type):
            if results is None:
                return None
            return_type = get_args(return_type)[0]
        if isinstance(return_type, type) and issubclass(return_type, BaseModel):
            results = return_type.model_validate_json(results)
        return results
        
        