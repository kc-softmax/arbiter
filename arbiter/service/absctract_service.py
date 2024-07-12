import inspect
import asyncio
from typing import Generic, TypeVar, Any
from arbiter.constants import (
    ARBITER_SERVICE_HEALTH_CHECK_INTERVAL,
    ARBITER_SERVICE_TIMEOUT,
    ARBITER_SYSTEM_CHANNEL,
)
from arbiter.constants.protocols import TaskProtocol
from arbiter.constants.enums import ArbiterMessageType
from arbiter.constants.data import ArbiterSystemMessage, ArbiterSystemRequestMessage
from arbiter.broker import MessageBrokerInterface, subscribe_task, periodic_task

T = TypeVar('T', bound=MessageBrokerInterface)


class ServiceMeta(type):

    def __new__(cls, name: str, bases: tuple, class_dict: dict[str, Any]):

        new_cls = super().__new__(cls, name, bases, class_dict)

        tasks: list[TaskProtocol] = []

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

        # parameter type check
        for task in tasks:
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
        setattr(new_cls, 'depth', len(new_cls.mro()) - 3)  # TODO enum
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
    auto_start = True

    def __init__(
        self,
        broker_type: type[T],
    ):
        self.force_stop = False
        self.broker_type = broker_type
        self.broker = broker_type()

        self.health_check_task: asyncio.Task = None
        self.health_check_time = 0

    @classmethod
    async def launch(cls, node_id: str, service_id: str):
        instance = cls()
        setattr(instance, 'node_id', node_id)
        setattr(instance, 'service_id', service_id)
        service = asyncio.create_task(instance.start())
        result = await service
        return result

    async def get_service(self):
        return self

    async def health_check_func(self) -> str:
        if not self.health_check_time:
            self.health_check_time = asyncio.get_event_loop().time()
        while True and not self.force_stop:
            try:
                start_time = asyncio.get_event_loop().time()
                if start_time - self.health_check_time > ARBITER_SERVICE_TIMEOUT:
                    break
                if start_time - self.health_check_time > ARBITER_SERVICE_HEALTH_CHECK_INTERVAL:
                    response = await self.broker.send_arbiter_message(
                        self.node_id,
                        ArbiterSystemRequestMessage(
                            from_id=self.service_id,
                            type=ArbiterMessageType.PING,
                        ).encode()
                    )
                    if response:
                        self.health_check_time = asyncio.get_event_loop().time()
                    else:
                        print(
                            f"{self.__class__.__name__} Response Empty, Health Check Failed")
                        break
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                return "Health Check Cancelled"
        if self.force_stop:
            return 'Force Stop from System'
        return 'Health Check Finished'

    async def on_start(self):
        pass
    
    async def on_shutdown(self):
        pass

    async def shutdown(
        self,
        dynamic_tasks: list[asyncio.Task]
    ):
        for dynamic_task in dynamic_tasks:
            dynamic_task and dynamic_task.cancel()

        self.health_check_task and self.health_check_task.cancel()
        await self.broker.send_arbiter_message(
            self.node_id,
            ArbiterSystemRequestMessage(
                from_id=self.service_id,
                type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
            ).encode(), 
            False,
        )
        await self.broker.disconnect()
        await self.on_shutdown()

    async def start(self):
        """
        서비스가 시작되면, manage_task를 통해 initialize 하는 과정을 진행하고,
        initialize가 완료되면 consuming_task와 start_task를 실행합니다.
        """
        assert self.service_id, "Service ID is not set"
        await self.broker.connect()
        dynamic_tasks: list[asyncio.Task] = []
        try:
            response = await self.broker.send_arbiter_message(
                self.node_id,
                ArbiterSystemRequestMessage(
                    from_id=self.service_id,
                    type=ArbiterMessageType.ARBITER_SERVICE_REGISTER,
                ).encode()
            )
            if not response:
                raise Exception("Failed to register service")
            response = ArbiterSystemMessage.decode(response)

            if response.type != ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK:
                raise Exception("message type is not correct")
            # TODO udpate service_id
            self.health_check_task = asyncio.create_task(
                self.health_check_func())

            for task in self.tasks:
                dynamic_tasks.append(
                    asyncio.create_task(task(self))
                )
            await self.on_start()
            await self.health_check_task

        except Exception as e:
            print(e)
        finally:
            await self.shutdown(dynamic_tasks)

    # 구독을 동적으로 해야한다....
    @subscribe_task(channel=ARBITER_SYSTEM_CHANNEL) # Master Channel 인데 바꿔야 한다
    async def get_system_message(self, message: bytes):
        system_message = ArbiterSystemMessage.decode(message)
        match system_message.type:
            case ArbiterMessageType.SHUTDOWN:
                self.force_stop = True
                # main arbiter가 비정상적으로 종료되었을때 온다.
                # 정상적으로 종료되면, arbiter가 모든 서비스에게 stop 메세지를 보내고 종료한다.

    @periodic_task(period=1)
    async def listener(self, messages: list[bytes]):
        if messages:
            self.force_stop = True
            for raw_message in messages:
                message = ArbiterSystemMessage.decode(raw_message)
                # print(message)
