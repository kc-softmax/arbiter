from __future__ import annotations
import pickle
import json
import inspect
import asyncio
import pickle
import uuid
from typing import  Any, Callable
from pydantic import BaseModel
from arbiter.enums import NodeState
from arbiter.constants import (
    HEALTH_CHECK_RETRY,
    ARBITER_SERVICE_HEALTH_CHECK_FUNC_CLOCK,
    ARBITER_SERVICE_HEALTH_CHECK_INTERVAL,
    ARBITER_SERVICE_TIMEOUT,
)
from arbiter.data.models import ArbiterServiceNode, ArbiterServerNode, ArbiterNode
from arbiter.utils import get_task_queue_name, get_pickled_data
from arbiter.exceptions import ArbiterServiceHealthCheckError
from arbiter import Arbiter

class ServiceMeta(type):

    def __new__(cls, name: str, bases: tuple, class_dict: dict[str, Any]):
        new_cls = super().__new__(cls, name, bases, class_dict)

        task_functions: list[Callable] = []

        combined_attrs = set(class_dict.keys())
        for base in bases:
            combined_attrs.update(dir(base))
            # 부모 클래스에서 decorator 수집
            for attr_name in dir(base):
                if (
                    callable(getattr(base, attr_name)) and
                    getattr(
                        getattr(base, attr_name),
                        'is_task_function', False)
                ):
                    task_functions.append(getattr(base, attr_name))

        # 현재 클래스에서 decorator 수집
        for attr_name, attr_value in class_dict.items():
            if (
                callable(attr_value) and getattr(
                    attr_value, 'is_task_function', False)
            ):
                task_functions.append(attr_value)
        # 각각이 중복되지 않는지 확인

        # start, shutdown attribute가 있는지 확인한다.
        if 'start' not in combined_attrs:
            raise AttributeError(
                f"The class {name} must have a start attribute.")

        if 'shutdown' not in combined_attrs:
            raise AttributeError(
                f"The class {name} must have a shutdown attribute.")

        depth = len(new_cls.mro()) - 3
        if depth < 0:
            return new_cls
        for task_function in task_functions:
            signature = inspect.signature(task_function)
            
            # Print the parameters of the function
            for index, param in enumerate(signature.parameters.values()):
                if param.name == 'self':
                    continue
                param_type = param.annotation
                # Ensure the parameter has a type hint
                if param_type is inspect._empty:
                    raise TypeError(
                        "No type hint provided, Task function must have a type hint")
                else:
                    # Example check if the first argument is User instance
                    # if task.auth and index == 1:
                    #     if param_type is not User:
                    #         raise TypeError(
                    #             f"if auth is True,\n{
                    #                 name} - {rpc_func.__name__} function must have a User instance as the second argument"
                    #         )
                    pass
        setattr(new_cls, 'task_functions', task_functions)
        return new_cls

class ArbiterService(metaclass=ServiceMeta):
    
    task_functions: list[Callable] = []

    num_of_services = 1
    master_only = False
    auto_start = True

    def __init__(
        self,
        service_id: str,
        broker_host: str,
        broker_port: int,
        broker_password: str,
    ):
        self.service_id = service_id
        self.force_stop = False

        self.service_node: ArbiterServiceNode | ArbiterServerNode = None
        self.arbiter_node: ArbiterNode = None
        
        self.arbiter = Arbiter(
            broker_host,
            broker_port,
            broker_password
        )
        self.system_subscribe_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.tasks: list[asyncio.Task] = []

    async def run(self):
        await self.arbiter.connect()
        await self.start()
        await self.shutdown()
        await self.arbiter.disconnect()
        
    async def on_start(self):
        pass
    
    async def start(self):
        error = None
        try:
            self.service_node = await self.arbiter.get_data(ArbiterServiceNode, self.service_id)
            if not self.service_node:
                self.service_node = await self.arbiter.get_data(ArbiterServerNode, self.service_id)
            
            self.arbiter_node = await self.arbiter.get_data(ArbiterNode, self.service_node.arbiter_node_id)
            
            self.health_check_task = asyncio.create_task(
                self.health_check_func())
            
            self.system_subscribe_task = asyncio.create_task(
                self.listen_system_func())

            for task_function in self.task_functions:
                queue = getattr(task_function, 'queue', None)
                num_of_tasks = getattr(task_function, 'num_of_tasks', 1)
                if not queue:
                    queue = get_task_queue_name(
                        self.__class__.__name__, 
                        task_function.__name__)
                params = [self.arbiter, queue, self]
                for _ in range(num_of_tasks):
                    self.tasks.append(
                        asyncio.create_task(task_function(*params)))

            await self.on_start()            
            self.service_node.state = NodeState.ACTIVE
            await self.arbiter.save_data(self.service_node)
            await self.health_check_task
        except Exception as e:
            error = e
        finally:
            if error:
                self.service_node.state = NodeState.ERROR
            else:
                self.service_node.state = NodeState.INACTIVE
            await self.arbiter.save_data(self.service_node)

    async def on_shutdown(self):
        pass

    async def shutdown(self):
        for task in self.tasks:
            task and task.cancel()
        self.system_subscribe_task and self.system_subscribe_task.cancel()
        self.health_check_task and self.health_check_task.cancel()
        await self.on_shutdown()
        await self.arbiter.disconnect()

    async def health_check_func(self) -> str:
        health_check_time = asyncio.get_event_loop().time()
        health_check_attempt = 0
        while True and not self.force_stop:
            try:
                start_time = asyncio.get_event_loop().time()
                
                if start_time - health_check_time > ARBITER_SERVICE_TIMEOUT:
                    break

                if start_time - health_check_time < ARBITER_SERVICE_HEALTH_CHECK_INTERVAL:
                    await asyncio.sleep(ARBITER_SERVICE_HEALTH_CHECK_FUNC_CLOCK)
                    continue
                
                health_check_time = asyncio.get_event_loop().time()
                message_id = await self.arbiter.send_message(
                    self.arbiter_node.get_health_check_channel(),
                    self.service_id)
                # test message_id is None
                response = await self.arbiter.get_message(message_id)
                if response:
                    health_check_time = asyncio.get_event_loop().time()
                    continue
                
                if health_check_attempt > HEALTH_CHECK_RETRY:
                    raise ArbiterServiceHealthCheckError()
                
                health_check_attempt += 1
            except asyncio.CancelledError:
                break
            except ArbiterServiceHealthCheckError:
                break            
            except Exception as e:
                print('unexpected error', e)
                break
                
    
    async def listen_system_func(self):
        async for message in self.arbiter.subscribe_listen(
            channel=self.arbiter_node.get_system_channel()
        ):
            try:
                message = message.decode()
                if message == self.arbiter_node.shutdown_code:
                    self.force_stop = True
                    break
            except Exception as e:
                print("Error in listen_system_func", e)
                print("Shutdown process start....")
                self.force_stop = True
                break
