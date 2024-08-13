import inspect
import asyncio
import pickle
import uuid
from typing import Generic, TypeVar, Any, Callable

from pydantic import BaseModel
from arbiter.constants import (
    ArbiterDataType,
    ArbiterTypedData,
    HEALTH_CHECK_RETRY,
    ARBITER_SERVICE_HEALTH_CHECK_INTERVAL,
    ARBITER_SERVICE_TIMEOUT
)
from arbiter.interface import subscribe_task, periodic_task
from arbiter.database.model import TaskFunction
from arbiter import Arbiter
from arbiter.utils import get_pickled_data
T = TypeVar('T', bound=Arbiter)


class ServiceMeta(type):

    def __new__(cls, name: str, bases: tuple, class_dict: dict[str, Any]):

        new_cls = super().__new__(cls, name, bases, class_dict)

        tasks: list[Callable] = []

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
                    tasks.append(getattr(base, attr_name))

        # 현재 클래스에서 decorator 수집
        for attr_name, attr_value in class_dict.items():
            if (
                callable(attr_value) and getattr(
                    attr_value, 'is_task_function', False)
            ):
                tasks.append(attr_value)

        # 각각이 중복되지 않는지 확인

        # start, shutdown attribute가 있는지 확인한다.
        if 'start' not in combined_attrs:
            raise AttributeError(
                f"The class {name} must have a start attribute.")

        if 'shutdown' not in combined_attrs:
            raise AttributeError(
                f"The class {name} must have a shutdown attribute.")

        depth = len(new_cls.mro()) - 3
        # parameter type check
        for task in tasks:
            if depth < 2:
                continue
            signature = inspect.signature(task)
            
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
        setattr(new_cls, 'tasks', tasks)
        setattr(new_cls, 'depth', depth)  # TODO enum
        return new_cls


# 이 구독을 하는 이유는, 발행을 검사하기 위함..? 구독 채널을 관리하기 위함이라고 생각하자


class AbstractService(Generic[T], metaclass=ServiceMeta):
    """
        Service 의 동작로직을 정의하는 추상클래스
        서비스는 instance화시 broker를 통해 consuming_task를 생성하고, start()를 호출하여 동작을 시작한다.
    """
    # set by metaclass
    decorator_exceptions = []
    tasks = []
    depth = 0

    # set by launch
    node_id: str = None
    service_id: str = None

    initial_processes = 1
    master_only = False
    auto_start = True

    def __init__(
        self,
        node_id: str,
        service_id: str,
        arbiter_type: type[T],
    ):
        self.node_id = node_id
        self.service_id = service_id
        self.force_stop = False
        self.arbiter_type = arbiter_type
        self.arbiter = arbiter_type()

        self.system_subscribe_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.health_check_time = 0

    @classmethod
    async def launch(
        cls,
        node_id: str, 
        service_id: str
    ):
        instance = cls(
            node_id,
            service_id
        )
        service = asyncio.create_task(instance.start())
        await instance.on_launch()
        result = await service
        return result

    async def on_launch(self):
        pass
    
    async def on_start(self):
        pass
    
    async def on_shutdown(self):
        pass

    async def get_service(self):
        return self

    async def health_check_func(self) -> str:
        if not self.health_check_time:
            self.health_check_time = asyncio.get_event_loop().time()
        health_check_retry = 0
        while True and not self.force_stop:
            try:
                start_time = asyncio.get_event_loop().time()
                if start_time - self.health_check_time > ARBITER_SERVICE_TIMEOUT:
                    break
                if start_time - self.health_check_time > ARBITER_SERVICE_HEALTH_CHECK_INTERVAL:
                    response = await self.arbiter.send_message(
                        receiver_id=self.node_id,
                        data=ArbiterTypedData(
                            type=ArbiterDataType.PING,
                            data=self.service_id).model_dump_json(),
                        wait_response=True)
                    if response:
                        self.health_check_time = asyncio.get_event_loop().time()
                    else:
                        health_check_retry += 1
                        if health_check_retry > HEALTH_CHECK_RETRY:
                            print(
                                f"{self.__class__.__name__} Response Empty, Health Check Failed")
                            break
                        else:
                            print(
                                f"{self.__class__.__name__} Response Empty, Retry {health_check_retry}")
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                return "Health Check Cancelled"
        # print(f"{self.__class__.__name__} Health Check Finished")
        if self.force_stop:
            return 'Force Stop from System'
        return 'Health Check Finished'

    async def shutdown(
        self,
        dynamic_tasks: list[asyncio.Task]
    ):
        await self.on_shutdown()
        for dynamic_task in dynamic_tasks:
            dynamic_task and dynamic_task.cancel()
        self.system_subscribe_task and self.system_subscribe_task.cancel()
        self.health_check_task and self.health_check_task.cancel()
        await self.arbiter.send_message(
            receiver_id=self.node_id,
            data=ArbiterTypedData(
                type=ArbiterDataType.ARBITER_SERVICE_UNREGISTER,
                data=self.service_id).model_dump_json())
        await self.arbiter.disconnect()

    async def start(self):
        """
        서비스가 시작되면, manage_task를 통해 initialize 하는 과정을 진행하고,
        initialize가 완료되면 consuming_task와 start_task를 실행합니다.
        """
        assert self.service_id, "Service ID is not set"
        await self.arbiter.connect()
        dynamic_tasks: list[asyncio.Task] = []
        try:
            response = await self.arbiter.send_message(
                receiver_id=self.node_id,
                data=ArbiterTypedData(
                    type=ArbiterDataType.ARBITER_SERVICE_REGISTER,
                    data=self.service_id).model_dump_json(),
                wait_response=True)
            if not response:
                raise Exception("Failed to register service")
            response = ArbiterDataType(int(response))
            if response != ArbiterDataType.ACK:
                raise Exception("message type is not correct")
            # TODO udpate service_id
            self.health_check_task = asyncio.create_task(
                self.health_check_func())
            self.system_subscribe_task = asyncio.create_task(
                self.get_system_message())

            for task in self.tasks:
                dynamic_tasks.append(
                    asyncio.create_task(task(self))
                )
            await self.on_start()
            await self.health_check_task

        except Exception as e:
            print(e, 'err')
        finally:
            await self.shutdown(dynamic_tasks)
    
    async def send_task(
        self,
        task_queue: str,
        data: str | bytes,
        wait_response: bool = False,
    ):
        # find task name
        response = await self.arbiter.send_message(
            receiver_id=task_queue,
            data=data,
            wait_response=wait_response)
        # 결과를 기다려야 하는데, 결과가 없다면, 어떻게 처리할 것인가?
        if wait_response:
            if not response:
                if not await self.arbiter.search_data(
                    TaskFunction,
                    task_queue=task_queue,
                ):                
                    raise Exception(f"Task Queue {task_queue} is not found")
        return response

    async def send_async_task(
        self,
        task_queue: str,
        data: str | bytes,
        timeout=5
    ):
        # if not await self.arbiter.search_data(
        #     TaskFunction,
        #     task_queue=task_queue,
        # ):                
        #     raise Exception(f"Task Queue {task_queue} is not found")
        try:
            response_queue = uuid.uuid4().hex
            await self.arbiter.push_message(
                task_queue,
                pickle.dumps((response_queue, data)))
            
            async for data in self.arbiter.listen_bytes(response_queue, timeout):
                if data is None:
                    break
                data = get_pickled_data(data)
                if isinstance(data, BaseModel):
                    data = data.model_dump()
                yield data
        except asyncio.CancelledError:
            pass
        

    async def get_system_message(self):
        async for message in self.arbiter.subscribe_listen(channel=self.node_id + '_system'):
            decoded_message = ArbiterTypedData.model_validate_json(message)
            data = decoded_message.data
            match decoded_message.type:
                case ArbiterDataType.SHUTDOWN:
                    if data == self.node_id:
                        self.force_stop = True
                case ArbiterDataType.MASTER_SHUTDOWN:
                    self.force_stop = True
                    # main arbiter가 비정상적으로 종료되었을때 온다.
                    # 정상적으로 종료되면, arbiter가 모든 서비스에게 stop 메세지를 보내고 종료한다.

    @periodic_task(period=1)
    async def listener(self, messages: list[bytes]):
        if messages:
            self.force_stop = True
            for raw_message in messages:
                pass
