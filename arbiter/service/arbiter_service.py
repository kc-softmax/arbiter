from __future__ import annotations
import inspect
import asyncio
import multiprocessing
import pickle
import time
from multiprocessing.synchronize import Event as EventType
from typing import  Any, Callable, Type
from typing_extensions import Annotated
from arbiter.enums import NodeState
from arbiter.data.models import (
    ArbiterTaskNode,
    ArbiterServiceNode,
    ArbiterNode
)
# from arbiter.utils import get_task_queue_name
# from arbiter.exceptions import ArbiterServiceHealthCheckError
# from arbiter.task.tasks import ArbiterAsyncTask
from arbiter.configs import ArbiterConfig
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
      
class ArbiterService:
    """
    Base class for Arbiter service.
    
    **Parameters**
    - `name` (str): The name of the service.
    - `gateway` (str): The gateway of the service, default is 'default', if not specified, the service will be registered to all gateways.
    - `load_timeout` (int): The timeout of loading service, default is 10.
    - `auto_start` (bool): The auto start of the service, when the service is created, default is False.
    """
    
    # task_functions: list[Callable] = []
    
    # # create async task로 생성되어 진다
    # """ use create async task """
    # async_task_functions: list[Callable] = []
    
    # """ use mutiprocesing """
    # parallel_task_functions: list[Callable] = []
    
    def __init__(
        self,
        *,
        name: str,
    ):
        self.name = name
        self.arbiter: Arbiter = None
        self.arbiter_node_id: int = None
        self.service_node: ArbiterServiceNode = None
        
        # config candidates

    def setup(
        self,
        arbiter_node_id: int,
    ):
        self.arbiter_node_id = arbiter_node_id
        self.service_node = ArbiterServiceNode(
            arbiter_node_id=arbiter_node_id,
            name=self.name,
            state=NodeState.INACTIVE,
        )
        return self.service_node.node_id

    def test(self):
        pass
    
    
    def health_check(
        self,
        queue: multiprocessing.Queue,
        event: EventType,
        service_node_id: str,
        health_check_interval: int,        
    ):
        while not event.is_set():
            queue.put_nowait(service_node_id)
            time.sleep(health_check_interval)
    
    async def run(
        self,
        queue: multiprocessing.Queue,
        event: EventType,
        arbiter_config: ArbiterConfig,
        health_check_interval: int,
    ):
        """
        Run the service.
        """
        self.arbiter = Arbiter(arbiter_config)
        await self.arbiter.connect()
        try:
            await self.on_start()
            ##############################
            # task 생성 및 실행
            # async_task_functions
            # parallel_task_functions
            
            ##############################
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.health_check,
                queue,
                event,
                self.service_node.node_id,
                health_check_interval)
            await self.on_shutdown()
            pass
        except Exception as e:
            await self.on_error(e)
        finally:
            await self.arbiter.disconnect()
    
    async def on_start(self):
        pass

    async def on_shutdown(self):
        pass
    
    async def on_error(self, error: Exception):
        pass
    

    # for task_function in self.task_functions:
    #     queue = getattr(task_function, 'queue', None)
    #     num_of_tasks = getattr(task_function, 'num_of_tasks', 1)
    #     if not queue:
    #         queue = get_task_queue_name(
    #             self.__class__.__name__, 
    #             task_function.__name__)
    #     task_model = await self.arbiter.get_data(ArbiterTaskModel, queue)
    #     if not task_model:
    #         raise ValueError(f"Task model {queue} not found")
    #     for _ in range(num_of_tasks):
    #         params = [self.arbiter, queue, self]
    #         task_node = ArbiterTaskNode(
    #             service_node_id=self.service_node_id,
    #             parent_model_id=task_model.id,
    #             state=NodeState.INACTIVE,
    #         )
    #         await self.arbiter.save_data(task_node)
    #         params.append(task_node)
    #         self.tasks[task_node] = asyncio.create_task(task_function(*params))