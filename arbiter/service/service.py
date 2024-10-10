from __future__ import annotations
import inspect
import asyncio
import pickle
from typing import  Any, Callable, Type
from typing_extensions import Annotated
from arbiter.enums import NodeState
from arbiter.data.models import (
    ArbiterTaskNode,
    ArbiterServiceNode, 
    ArbiterGatewayNode,
    ArbiterNode
)
from arbiter.utils import get_task_queue_name
from arbiter.exceptions import ArbiterServiceHealthCheckError
from arbiter.task.tasks import ArbiterAsyncTask
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
    """
    Base class for Arbiter service.
    
    **Parameters**
    - `name` (str): The name of the service.
    - `gateway` (str): The gateway of the service, default is 'default', if not specified, the service will be registered to all gateways.
    - `load_timeout` (int): The timeout of loading service, default is 10.
    - `log_level` (str): The log level of the service, default is 'info'.
    - `log_format` (str): The log format of the service, default is "[service_name] - %(level)s - %(message)s - %(datetime)s".
    - `auto_start` (bool): The auto start of the service, when the service is created, default is False.
    """
    
    task_functions: list[Callable] = []
    num_of_services = 1
    
    def __init__(
        self,
        *,
        name: str,
        load_timeout: int = 10,
        auto_start: bool = False,
        log_level: str | None = None,
        log_format: str | None = None
    ):
        self.name = name
        self.load_timeout = load_timeout
        self.log_level = log_level
        self.log_format = log_format
        self.auto_start = auto_start
        
        self.arbiter: Arbiter = None
        self.service_node_id: str = None
        self.force_stop = False
        self.service_node: ArbiterServiceNode | ArbiterGatewayNode = None
        self.arbiter_node: ArbiterNode = None
        self.system_subscribe_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.tasks: dict[ArbiterTaskNode, asyncio.Task] = {}

    async def setup(
        self,
        arbiter_name: str,
        service_node_id: str,
        arbiter_host: str,
        arbiter_port: int,
        arbiter_config: dict,
    ):
        self.service_node_id = service_node_id
        self.arbiter = Arbiter(
            arbiter_name,
            arbiter_host,
            arbiter_port,
            arbiter_config
        )
    
    def handle_task(self, task: ArbiterAsyncTask):
        self.task_functions.append(task)
    
    async def run(self):
        await self.arbiter.connect()
        try:
            await self.start()
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()
            await self.arbiter.disconnect()
    
    async def on_start(self):
        pass

    async def start(self):
        error = None
        try:
            self.service_node = await self._get_service_node()
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
                task_model = await self.arbiter.get_data(ArbiterTaskModel, queue)
                if not task_model:
                    raise ValueError(f"Task model {queue} not found")
                for _ in range(num_of_tasks):
                    params = [self.arbiter, queue, self]
                    task_node = ArbiterTaskNode(
                        service_node_id=self.service_node_id,
                        parent_model_id=task_model.id,
                        state=NodeState.INACTIVE,
                    )
                    await self.arbiter.save_data(task_node)
                    params.append(task_node)
                    self.tasks[task_node] = asyncio.create_task(task_function(*params))
            await self.on_start()            
            self.service_node.state = NodeState.ACTIVE
            await self.arbiter.save_data(self.service_node)
            await self.health_check_task
        except Exception as e:
            error = e
            print("Error in start", e, self.__class__.__name__)
        finally:
            if not self.service_node:
                return
            if error:
                self.service_node.state = NodeState.ERROR
            else:
                self.service_node.state = NodeState.INACTIVE
            await self.arbiter.save_data(self.service_node)

    async def on_shutdown(self):
        pass

    async def shutdown(self):
        for task_node, task in self.tasks.items():
            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass
            finally:
                task_node.state = NodeState.INACTIVE
                await self.arbiter.save_data(task_node)
        self.system_subscribe_task and self.system_subscribe_task.cancel()
        self.health_check_task and self.health_check_task.cancel()
        await self.on_shutdown()
        await self.arbiter.disconnect()

    async def health_check_func(self) -> str:
        service_timeout = self.arbiter.config.get('service_timeout')
        service_health_check_interval = self.arbiter.config.get('service_health_check_interval')
        service_health_check_func_clock = self.arbiter.config.get('service_health_check_func_clock')
        service_retry_count = self.arbiter.config.get('service_retry_count')
        health_check_time = asyncio.get_event_loop().time()
        health_check_attempt = 0
        while True and not self.force_stop:
            try:
                start_time = asyncio.get_event_loop().time()
                
                if start_time - health_check_time > service_timeout:
                    break

                if start_time - health_check_time < service_health_check_interval:
                    await asyncio.sleep(service_health_check_func_clock)
                    continue
                
                message_id = await self.arbiter.send_message(
                    self.arbiter_node.get_health_check_channel(),
                    self.service_node_id)
                # test message_id is None
                response = await self.arbiter.get_message(message_id)
                if response:
                    health_check_time = asyncio.get_event_loop().time()
                    continue
                
                if health_check_attempt > service_retry_count:
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
