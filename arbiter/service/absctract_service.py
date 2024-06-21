import time
import asyncio
from typing import Generic, TypeVar
from typing import Generic, TypeVar
from arbiter.constants import (
    ARBITER_SERVICE_HEALTH_CHECK_INTERVAL,
    ARBITER_SERVICE_TIMEOUT,
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_SYSTEM_QUEUE
)
from arbiter.constants.enums import ArbiterMessageType
from arbiter.constants.data import ArbiterSystemMessage, ArbiterSystemRequestMessage
from arbiter.broker import MessageBrokerInterface, subscribe_task, periodic_task

T = TypeVar('T', bound=MessageBrokerInterface)


class ServiceMeta(type):

    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)

        subscribe_funcs = []
        periodic_funcs = []
        rpc_funcs = []

        combined_attrs = set(dct.keys())
        for base in bases:
            combined_attrs.update(dir(base))
            # 부모 클래스에서 decorator 수집
            for attr_name in dir(base):
                if (
                    callable(getattr(base, attr_name)) and
                    getattr(getattr(base, attr_name),
                            'is_subscribe_decorated', False)
                ):
                    subscribe_funcs.append(
                        getattr(base, attr_name))

                if (
                    callable(getattr(base, attr_name)) and
                    getattr(getattr(base, attr_name),
                            'is_periodic_decorated', False)
                ):
                    periodic_funcs.append(
                        getattr(base, attr_name))

                if (
                    callable(getattr(base, attr_name)) and
                    getattr(getattr(base, attr_name),
                            'is_rpc_decorated', False)
                ):

                    rpc_funcs.append(
                        getattr(base, attr_name))

        # 현재 클래스에서 decorator 수집
        for attr_name, attr_value in dct.items():
            if (
                callable(attr_value) and
                getattr(attr_value, 'is_subscribe_decorated', False)
            ):
                subscribe_funcs.append(attr_value)
            if (
                callable(attr_value) and
                getattr(attr_value, 'is_periodic_decorated', False)
            ):
                periodic_funcs.append(attr_value)

            if (
                callable(attr_value) and
                getattr(attr_value, 'is_rpc_decorated', False)
            ):
                rpc_funcs.append(attr_value)

        # 각각이 중복되지 않는지 확인

        # start, shutdown attribute가 있는지 확인한다.
        if 'start' not in combined_attrs:
            raise AttributeError(
                f"The class {name} must have a start attribute.")

        if 'shutdown' not in combined_attrs:
            raise AttributeError(
                f"The class {name} must have a shutdown attribute.")

        setattr(new_cls, 'rpc_funcs', rpc_funcs)
        setattr(new_cls, 'periodic_funcs', periodic_funcs)
        setattr(new_cls, 'subscribe_funcs', subscribe_funcs)
        setattr(new_cls, 'depth', len(new_cls.mro()) - 3)  # TODO enum

        return new_cls


# 이 구독을 하는 이유는, 발행을 검사하기 위함..? 구독 채널을 관리하기 위함이라고 생각하자


class AbstractService(Generic[T], metaclass=ServiceMeta):
    """
        Service 의 동작로직을 정의하는 추상클래스
        서비스는 instance화시 broker를 통해 consuming_task를 생성하고, start()를 호출하여 동작을 시작한다.
    """
    # set by metaclass
    periodic_funcs = []
    rpc_funcs = []
    subscribe_funcs = []
    depth = 0

    def __init__(
        self,
        broker_type: type[T],
    ):
        self.service_id = None  # 등록 이 완료된 후 생성된다.
        self.force_stop = False
        self.broker_type = broker_type
        self.broker = broker_type()

        self.health_check_task: asyncio.Task = None
        self.health_check_time = 0

    @classmethod
    async def launch(cls, **kwargs):
        instance = cls()
        service = asyncio.create_task(instance.start())
        result = await service
        return result

    async def health_check_func(self) -> str:
        if not self.health_check_time:
            self.health_check_time = asyncio.get_event_loop().time()
        while True and not self.force_stop:
            start_time = asyncio.get_event_loop().time()
            if start_time - self.health_check_time > ARBITER_SERVICE_TIMEOUT:
                break
            if start_time - self.health_check_time > ARBITER_SERVICE_HEALTH_CHECK_INTERVAL:
                self.health_check_time = start_time
                response = await self.broker.send_message(
                    ARBITER_SYSTEM_QUEUE,
                    ArbiterSystemRequestMessage(
                        from_id=self.service_id,
                        type=ArbiterMessageType.PING,
                    ).encode()
                )
                if response:
                    self.health_check_time = start_time
                else:
                    break
            await asyncio.sleep(1)
        if self.force_stop:
            return 'Force Stop from System'
        return 'Health Check Finished'

    async def shutdown(
        self,
        dynamic_tasks: list[asyncio.Task]
    ):
        for dynamic_task in dynamic_tasks:
            dynamic_task and dynamic_task.cancel()

        self.health_check_task and self.health_check_task.cancel()
        response = await self.broker.send_message(
            ARBITER_SYSTEM_QUEUE,
            ArbiterSystemRequestMessage(
                from_id=self.service_id,
                type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
            ).encode(),
        )
        if not response:
            # cleanup
            print("Failed to unregister service")
            await self.broker.delete_message(self.service_id)
        await self.broker.disconnect()

    async def start(self):
        """
        서비스가 시작되면, manage_task를 통해 initialize 하는 과정을 진행하고,
        initialize가 완료되면 consuming_task와 start_task를 실행합니다.
        """
        await self.broker.connect()
        temporary_service_id = f"{self.__class__.__name__}_{time.time()}"
        response = await self.broker.send_message(
            ARBITER_SYSTEM_QUEUE,
            ArbiterSystemRequestMessage(
                from_id=temporary_service_id,
                type=ArbiterMessageType.ARBITER_SERVICE_REGISTER,
            ).encode()
        )
        if not response:
            raise Exception("Failed to register service")
        response = ArbiterSystemMessage.decode(response)
        if response.type != ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK:
            raise Exception("message type is not correct")

        # TODO udpate service_id
        self.service_id = response.data
        self.health_check_task = asyncio.create_task(self.health_check_func())

        dynamic_tasks: list[asyncio.Task] = []

        for subscribe_func in self.subscribe_funcs:
            dynamic_tasks.append(
                asyncio.create_task(subscribe_func(self))
            )
        for rpc_func in self.rpc_funcs:
            dynamic_tasks.append(
                asyncio.create_task(rpc_func(self))
            )

        for periodic_func in self.periodic_funcs:
            dynamic_tasks.append(
                asyncio.create_task(periodic_func(self))
            )

        result = await self.health_check_task

        print(f"{self.service_id} {self.__class__.__name__} service close - {result}")
        await self.shutdown(dynamic_tasks)

    @subscribe_task(channel=ARBITER_SYSTEM_CHANNEL)
    async def get_system_message(self, message: bytes):
        system_message = ArbiterSystemMessage.decode(message)
        match system_message.type:
            case ArbiterMessageType.SHUTDOWN:
                self.force_stop = True
                # main arbiter가 비정상적으로 종료되었을때 온다.
                # 정상적으로 종료되면, arbiter가 모든 서비스에게 stop 메세지를 보내고 종료한다.
            case ArbiterMessageType.ARBITER_SERVICE_UNREGISTER:
                await self.handle_service_unregistered(system_message.data)

    @periodic_task(period=1)
    async def service_handler(self, messages: list[bytes]):
        if messages:
            self.force_stop = True
            for raw_message in messages:
                message = ArbiterSystemMessage.decode(raw_message)
                # print(message)

    async def handle_service_unregistered(self, service_id: str):
        pass
