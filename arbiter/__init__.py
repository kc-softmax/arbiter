from __future__ import annotations
import asyncio
import sys
import uuid
import atexit
import signal
import os
import importlib
import time
import ast
import functools
import inspect
from asyncio.subprocess import Process
from contextlib import asynccontextmanager
from warnings import warn
from collections import defaultdict
from typing import AsyncGenerator, Callable, Type, TypeVar, Generic
from datetime import datetime
from arbiter.broker import RedisBroker
from arbiter.database import Database
from arbiter.database.model import Service, ServiceMeta, TaskFunction
from arbiter.service import AbstractService
from arbiter.constants import (
    ARBITER_SYSTEM_INITIAL_TIMEOUT,
    ARBITER_SERVICE_PENDING_TIMEOUT,
    ARBITER_SERVICE_ACTIVE_TIMEOUT,
    ARBITER_SYSTEM_TIMEOUT,
    ARBITER_SERVICE_SHUTDOWN_TIMEOUT,
    ARBITER_SYSTEM_CHANNEL,
)
from arbiter.constants.data import (
    ArbiterSystemRequestMessage,
    ArbiterSystemMessage,
    ArbiterMessage,
)
from arbiter.constants.enums import (
    ArbiterInitTaskResult,
    ArbiterShutdownTaskResult,
    ArbiterMessageType,
    ServiceState
)
from arbiter.utils import (
    find_python_files_in_path,
    get_all_subclasses,
    to_snake_case
)
T = TypeVar('T')


class TypedQueue(asyncio.Queue, Generic[T]):
    async def get(self) -> T:
        return await super().get()


class Arbiter:

    @property
    async def services(self) -> list[ServiceMeta]:
        return await self.db.fetch_service_meta()

    @property
    async def active_services(self) -> list[Service]:
        return await self.db.find_services(states=[ServiceState.ACTIVE])

    def __init__(self):
        self.node_id = str(uuid.uuid4())
        self.broker: RedisBroker = None
        self.system_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None

        self.pending_service_queue: TypedQueue[Service] = TypedQueue()
        # 동기화 한다.
        self._initial_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown_queue: asyncio.Queue = asyncio.Queue()
        self.shutdown_code = str(uuid.uuid4())
        self.db = Database.get_db()

    async def clear(self):
        if self.system_task:
            self.system_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        await self.db.disconnect()
        await self.broker.disconnect()

    async def register_services_meta(self, **kwargs) -> list[ServiceMeta]:
        from arbiter.api.api_service import ApiService
        python_files_in_root = find_python_files_in_path()
        # 서비스 파일(root아래)들을 import
        for python_file in python_files_in_root:
            importlib.import_module(python_file)

        # import 되었으므로 AbstractService의 subclasses로 접근 가능
        service_meta_list = []
        for service in get_all_subclasses(AbstractService):
            assert issubclass(service, AbstractService)
            if service.depth < 2:
                continue
            service_meta = await self.db.create_service_meta(
                service_name=service.__name__,
                service_module_name=service.__module__,
                tasks=service.tasks,
                initial_processes=service.initial_processes)
            service_meta_list.append(service_meta)
        return service_meta_list

    async def register_service(self, service_id: str):
        if service := await self.db.get_data(service_id, Service):
            await self.db.update_data(
                service,
                state=ServiceState.ACTIVE
            )
            return True
        return False

    async def unregister_service(
        self,
        service: Service,
        description: str = None
    ):
        # cli 등에서 실행 가능
        await self.db.update_data(
            service,
            state=ServiceState.INACTIVE,
            description=description,
        )

    async def _setup_shutdown_task(self):
        # api, arbiter main task를 제외한 나머지 서비스들을 중단한다.
        # 다른 서비스 종료방법 1
        # 곧 종료될 것이므로 신경쓰지 않는다. 하지만 각 서비스들에의 health_check_func에서 예외가 발생하여 종료될 것이다.
        await self.broker.broadcast(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterSystemMessage(
                type=ArbiterMessageType.SHUTDOWN,
            ).encode()
        )
        start_time = time.time()
        while True:
            if time.time() - start_time > ARBITER_SERVICE_SHUTDOWN_TIMEOUT:
                # 서비스가 종료되지 않았기 때문에 확인하는 메세지를 보내야한다.
                # 종료되지 않은 서비스들이 있기 때문에 확인해야 한다.
                await self._shutdown_queue.put(
                    (ArbiterShutdownTaskResult.WARNING, None)
                )
                break
            if not await self.active_services:
                await self._shutdown_queue.put(
                    (ArbiterShutdownTaskResult.SUCCESS, None)
                )
                break
            await asyncio.sleep(0.5)

        await self._shutdown_queue.put(None)

    async def shutdown_task(self) -> AsyncGenerator[tuple[ArbiterShutdownTaskResult, str], None]:
        """
            shout down
            1. unregister all services with arbiter, api
            2. stop api service
            3. wait for all tasks to finish
            4. disconnect db
            5. disconnect broker
        """
        await self.pending_service_queue.put(None)
        asyncio.create_task(self._setup_shutdown_task())
        while True:
            message = await self._shutdown_queue.get()
            if message == None:
                break
            yield message
        await self.broker.send_message(
            self.node_id,
            ArbiterSystemRequestMessage(
                from_id=self.shutdown_code,
                type=ArbiterMessageType.SHUTDOWN
            ).encode(),
            None)

        self.shutdown_code = None
        await self.system_task
        await self.health_check_task

    async def _setup_initial_task(self):
        async def check_initial_services(timeout: int) -> list[Service]:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if not await self.db.find_services(states=[ServiceState.PENDING]):
                    return []
                await asyncio.sleep(0.5)
            return await self.db.find_services(states=[ServiceState.PENDING])

        if pending_services := await check_initial_services(ARBITER_SYSTEM_INITIAL_TIMEOUT):
            # failed to start all services
            # 실패한 서비스들을 어떻게 처리할 것인가? 쓰는사람에게 맡긴다.
            pending_service_names = ', '.join(
                [service.service_meta.name for service in pending_services])
            await self._initial_queue.put(
                (ArbiterInitTaskResult.FAIL, pending_service_names))
        else:
            await self._initial_queue.put(
                (ArbiterInitTaskResult.SUCCESS, None))

        await self._initial_queue.put(None)

    async def initial_task(self) -> AsyncGenerator[tuple[ArbiterInitTaskResult, str], None]:
        while True:
            message = await self._initial_queue.get()
            if message == None:
                break
            yield message

    @asynccontextmanager
    async def start(self) -> AsyncGenerator[Arbiter, Exception]:
        await self.db.connect()
        await self.db.initialize()
        self.broker = RedisBroker()
        await self.broker.connect()
        try:
            service_meta_list = await self.register_services_meta()
        except Exception as e:
            await self.clear()
            yield e
            return

        self.system_task = asyncio.create_task(self.system_task_func())

        for service_meta in service_meta_list:
            for _ in range(service_meta.initial_processes):
                await self.pending_service_queue.put(
                    await self.db.create_data(
                        Service,
                        state=ServiceState.PENDING,
                        service_meta=service_meta
                    )
                )
            # TODO 확인해야 한다, 서비스가 정상적으로 켜진건지 할 수  있다면
            # 만약 켜지지 않았다면, new_service 객체를 바탕으로 조정해야 한다.
            # process = asyncio.create_task(self.start_service(new_service))
            # processes.append(process)
        asyncio.create_task(self._setup_initial_task())

        self.health_check_task = asyncio.create_task(
            self.health_check_func())

        yield self

        await self.clear()

    # @asynccontextmanager
    # async def start_service(self, service: Service) -> AsyncGenerator[Process, None]:

    #     command = get_running_command(
    #         service.service_meta.module_name,
    #         service.service_meta.name,
    #         service.id,
    #         self.node_id
    #     )
    #     proc = await asyncio.create_subprocess_shell(
    #         f'{sys.executable} -c "{command}"',
    #         stdout=asyncio.subprocess.PIPE,
    #         stderr=asyncio.subprocess.PIPE,
    #         shell=True
    #     )
    #     yield proc
    #     await proc.wait()

    async def stop_services(self, service_ids: list[int]):
        for service_id in service_ids:
            service = await self.db.get_data(service_id, Service)
            if service and service.state == ServiceState.ACTIVE:
                target = f"{to_snake_case(
                    service.service_meta.name)}_service_handler"
                await self.broker.send_message(
                    target,
                    ArbiterSystemMessage(
                        type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
                    ).encode(), None
                )

    async def health_check_func(self):
        while not self.system_task.done():
            current_time = time.time()
            description = ''
            removed_services = []
            pending_or_active_services = await self.db.find_services(
                states=[ServiceState.PENDING, ServiceState.ACTIVE])
            for service in pending_or_active_services:
                elapsed_time = current_time - service.updated_at.timestamp()
                if service.state == ServiceState.ACTIVE:
                    description = 'Service is not responding.'
                    timeout = ARBITER_SERVICE_ACTIVE_TIMEOUT
                elif service.state == ServiceState.PENDING:
                    description = f'Service is not started within {
                        elapsed_time} seconds.'
                    timeout = ARBITER_SERVICE_PENDING_TIMEOUT
                else:
                    raise ValueError('Invalid Service State')
                if elapsed_time > timeout:
                    removed_services.append((service, description))

            for removed_service in removed_services:
                await self.unregister_service(*removed_service)

            await asyncio.sleep(0.5)

    async def system_task_func(self):
        while True:

            request_json = await self.broker.client.blpop(
                self.node_id, timeout=ARBITER_SYSTEM_TIMEOUT)
            if request_json:
                try:
                    message = ArbiterMessage.decode(request_json[1])
                    requset_message = ArbiterSystemRequestMessage.decode(
                        message.data)
                    from_service_id = requset_message.from_id
                    response = None
                    match requset_message.type:
                        case ArbiterMessageType.PING:
                            # health check의 경우 한번에 모아서 업데이트 하는 경우를 생각해봐야한다.
                            if service := await self.db.get_data(from_service_id, Service):
                                if service.state == ServiceState.PENDING:
                                    warn('Service is not registered yet.')
                                elif service.state == ServiceState.INACTIVE:
                                    warn(
                                        """
                                        Service is inactive, but service try
                                        to send ping message.
                                        please check the service and
                                        service shutdown process.
                                        """)
                                else:
                                    await self.db.update_data(service)
                                    response = ArbiterSystemMessage(
                                        type=ArbiterMessageType.PONG
                                    )
                        case ArbiterMessageType.ARBITER_SERVICE_REGISTER:
                            if await self.register_service(from_service_id):
                                response = ArbiterSystemMessage(
                                    type=ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK
                                )
                        case ArbiterMessageType.ARBITER_SERVICE_UNREGISTER:
                            if unregistered_service := await self.db.get_data(from_service_id, Service):
                                await self.unregister_service(unregistered_service)
                                response = ArbiterSystemMessage(
                                    type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER_ACK,
                                )
                        case ArbiterMessageType.SHUTDOWN:
                            if self.shutdown_code == from_service_id:
                                break
                except Exception as e:
                    print('Error: ', e)
                    print('Request: ', request_json)
                    print('Message: ', message)
                    print("Request Message: ", requset_message)
                    response = ArbiterSystemMessage(
                        message_type=ArbiterMessageType.ERROR,
                        data=str(e)
                    )
                message.id and response and await self.broker.push_message(
                    message.id,
                    response.encode()
                )
            else:
                # Timeout 발생
                # Arbiter 상태 확인
                # Arbiter Shutdown
                print('Timeout break, Arbiter Shutdown')
                break
        if self.shutdown_code:
            # pending_service_queue에 None을 넣어서
            # cli의 종료를 유도하여 shutdown_task를 실행한다.
            await self.pending_service_queue.put(None)


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))
