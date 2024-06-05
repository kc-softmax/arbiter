import time
import asyncio
from typing import Generic, TypeVar
from abc import ABC, abstractmethod
from arbiter.constants import (
    ARBITER_SERVICE_HEALTH_CHECK_INTERVAL,
    ARBITER_SERVICE_TIMEOUT,
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_SYSTEM_QUEUE,
    ArbiterMessageType,
    ArbiterMessage
)
from arbiter.broker import MessageBrokerInterface
T = TypeVar('T', bound=MessageBrokerInterface)


class AbstractService(ABC, Generic[T]):
    """
        Service 의 동작로직을 정의하는 추상클래스
        서비스는 instance화시 broker를 통해 consuming_task를 생성하고, start()를 호출하여 동작을 시작한다.
    """

    def __init__(
        self,
        broker_type: type[T],
        frequency: float = 60.0,
    ):
        """
            frequency
            Service의 ID의 경우 기존 서비스 이름 + 숫자 형식으로 생성되거나,
            기존 서비스 ID + 숫자를 hash 형식으로 생성된다.
        """
        self.service_id = None  # 등록 이 완료된 후 생성된다.
        self.frequency = frequency
        self.broker_type = broker_type
        self.broker = broker_type()
        self.system_listen_task: asyncio.Task = None
        self.incoming_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.service_worker: asyncio.Task = None
        self.health_check_time = 0

    @classmethod
    def launch(cls, **kwargs):
        instance = cls()
        loop = asyncio.new_event_loop()
        loop.run_until_complete(instance.service_start())

    async def system_listen_task_func(self) -> str:
        await self.broker.subscribe(ARBITER_SYSTEM_CHANNEL)
        async for message in self.broker.listen():
            await self.get_system_message(ArbiterMessage.decode(message))
        await self.broker.unsubscribe(ARBITER_SYSTEM_CHANNEL)
        return 'System Listen finished'

    async def incoming_task_func(self) -> str:
        await self.broker.subscribe(self.service_id)
        async for message in self.broker.listen():
            await self.get_message(message)
        await self.broker.unsubscribe(self.service_id)
        return 'Incomig Task finished'

    async def health_check_func(self) -> str:
        if not self.health_check_time:
            self.health_check_time = asyncio.get_event_loop().time()
        while True:
            start_time = asyncio.get_event_loop().time()
            if start_time - self.health_check_time > ARBITER_SERVICE_TIMEOUT:
                break
            if start_time - self.health_check_time > ARBITER_SERVICE_HEALTH_CHECK_INTERVAL:
                self.health_check_time = start_time
                response = await self.broker.send_request_and_wait_for_response(
                    ARBITER_SYSTEM_QUEUE,
                    ArbiterMessage(
                        from_service_id=self.service_id,
                        message_type=ArbiterMessageType.PING,
                    )
                )
                if response:
                    self.health_check_time = start_time
                else:
                    break
            await asyncio.sleep(1)
        return 'Health Check Finished'

    async def service_worker_func(self) -> str:
        while True:
            start_time = asyncio.get_event_loop().time()
            if not await self.service_work():
                break
            elapsed_time = asyncio.get_event_loop().time() - start_time
            sleep_time = max(0, (1 / self.frequency) - elapsed_time)
            await asyncio.sleep(sleep_time)
        return 'Service Worker Finished'

    async def service_stop(self):
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.service_worker:
            self.service_worker.cancel()
        if self.incoming_task:
            self.incoming_task.cancel()
        if self.system_listen_task:
            self.system_listen_task.cancel()
        response = await self.broker.send_request_and_wait_for_response(
            ARBITER_SYSTEM_QUEUE,
            ArbiterMessage(
                from_service_id=self.service_id,
                message_type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
            ),
        )
        if not response:
            # cleanup
            print("Failed to unregister service")
            await self.broker.delete_message(self.service_id)

        await self.broker.disconnect()

    async def service_start(self):
        """
        서비스가 시작되면, manage_task를 통해 initialize 하는 과정을 진행하고,
        initialize가 완료되면 consuming_task와 start_task를 실행합니다.
        """
        #     if not self.worker or self.worker.done():
        # self.worker = asyncio.create_task(self.worker_func())
        await self.broker.connect()
        self.system_listen_task = asyncio.create_task(
            self.system_listen_task_func())
        temporary_service_id = f"{self.__class__.__name__}_{time.time()}"
        response = await self.broker.send_request_and_wait_for_response(
            ARBITER_SYSTEM_QUEUE,
            ArbiterMessage(
                from_service_id=temporary_service_id,
                message_type=ArbiterMessageType.ARBITER_SERVICE_REGISTER,
            )
        )
        if not response or response.message_type != ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK:
            raise Exception("Failed to register service")
        self.service_id = response.data
        self.incoming_task = asyncio.create_task(self.incoming_task_func())
        self.service_worker = asyncio.create_task(self.service_worker_func())
        self.health_check_task = asyncio.create_task(self.health_check_func())
        done, _ = await asyncio.wait(
            [
                self.health_check_task,
                self.service_worker,
                self.incoming_task,
            ],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            result = await task
            print(f"Service close : {result}")
        await self.service_stop()

    async def get_system_message(self, message: ArbiterMessage):
        match message.message_type:
            case ArbiterMessageType.SHUTDOWN:
                await self.handle_arbiter_shutdown(message.data)
            case ArbiterMessageType.ARBITER_SERVICE_UNREGISTER:
                await self.handle_service_unregistered(message.data)

    async def handle_service_unregistered(self, service_id: str):
        pass

    async def handle_arbiter_shutdown(self, data: any = None):
        pass

    @abstractmethod
    async def get_message(self, message: bytes):
        pass

    @abstractmethod
    async def service_work(self) -> bool:
        NotImplementedError("service_work method must be implemented")
