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
from collections import defaultdict
from typing import Callable
from datetime import datetime
from arbiter.broker import RedisBroker
from arbiter.database import Database
from arbiter.database.model import Service, ServiceMeta, RpcFunction
from arbiter.service import AbstractService
from arbiter.constants import (
    ARBITER_SERVICE_TIMEOUT,
    ARBITER_SYSTEM_TIMEOUT,
    ARBITER_SYSTEM_SERVICE_ID,
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_SYSTEM_QUEUE,
)
from arbiter.constants.data import (
    ArbiterSystemRequestMessage,
    ArbiterSystemMessage,
    ArbiterMessage,
)
from arbiter.constants.enums import (
    ArbiterMessageType,
    ServiceState
)
from arbiter.utils import (
    find_python_files_in_path,
    get_running_command,
    get_all_subclasses
)


class Arbiter:

    @property
    async def services(self) -> list[ServiceMeta]:
        return await self.db.fetch_service_meta()

    @property
    async def active_services(self) -> list[Service]:
        return await self.db.find_services(state=ServiceState.ACTIVE)

    def __init__(self):
        self.redis_broker: RedisBroker = None
        self.system_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.current_services: list[Service] = []
        self.registered_services: list[type[AbstractService]] = []
        self.unregister_service_names: list[str] = []
        # 동기화 한다.
        self.shutdown_code = str(uuid.uuid4())
        self.health_map: dict[int, int] = {}
        self.db = Database()

    async def clear(self):
        if self.system_task:
            self.system_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        await self.db.disconnect()
        await self.redis_broker.disconnect()

    async def start(self, **kwargs):
        await self.db.connect()
        await self.db.initialize()
        await self.register_services_meta()

        self.redis_broker = RedisBroker()
        await self.redis_broker.connect()

        self.system_task = asyncio.create_task(self.system_task_func())

        self.health_check_task = asyncio.create_task(self.health_check_func())

        # 현재는 의미없는 코드이다.
        # clear할때 전부 지우기 때문에,
        if active_services := await self.active_services:
            for active_service in active_services:
                self.health_map[active_service.id] = active_service.updated_at.timestamp(
                )

        for service in self.registered_services:
            asyncio.create_task(self.start_service(service.__name__))
        await self.health_check_task

        # broker를 통해 main이 shutdown 되었다고 알린다.
        # # TODO 정상적이지 않은 shutdownd에 관해서 처리
        # await self.redis_broker.broadcast(
        #     ARBITER_SYSTEM_CHANNEL,
        #     ArbiterSystemMessage(message_type=ArbiterMessageType.SHUTDOWN).encode())
        await self.clear()

    async def shutdown_task(self):
        # api, arbiter main task를 제외한 나머지 서비스들을 중단한다.
        # 다른 서비스 종료방법 1
        # self.health_map.clear() 하면 main health_check_func은 올바르게 동작하지 않지만
        # 곧 종료될 것이므로 신경쓰지 않는다. 하지만 각 서비스들에의 health_check_func에서 예외가 발생하여 종료될 것이다.
        # self.health_map.clear()
        await self.redis_broker.broadcast(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterSystemMessage(
                type=ArbiterMessageType.SHUTDOWN,
            ).encode()
        )
        start_time = time.time()
        while True:
            if time.time() - start_time > 10:
                # 서비스가 종료되지 않았기 때문에 확인하는 메세지를 보내야한다.
                # 경고메세지 출력
                print('Some services are not stopped yet...')
                break
            if not await self.active_services:
                break

            await asyncio.sleep(1)

        # # 종료 메세지가 오지 않은 서비스들에 대한 처리
        # 마찬가지로 현재는 처리할 필요가 없지만, 나중에는 처리해야 한다.
        # for to_remove_service in await Database.find_services(state='active'):
        #     await self.unregister_service(to_remove_service.id, 'stop_error')

    async def shutdown(self):
        """
            shout down
            1. unregister all services with arbiter, api
            2. stop api service
            3. wait for all tasks to finish
            4. disconnect prisma
            5. disconnect broker
        """
        print('shutdown.. please waiting for few seconds..')
        stop_task = asyncio.create_task(self.shutdown_task())
        await stop_task
        print('all services are stopped')
        # cancel system task nataurally

        await self.redis_broker.send_message(
            ARBITER_SYSTEM_QUEUE,
            ArbiterSystemRequestMessage(
                from_id=self.shutdown_code,
                type=ArbiterMessageType.SHUTDOWN
            ).encode(), 0)
        await self.system_task
        await self.health_check_task

    async def register_services_meta(self, **kwargs):
        from arbiter.api.api_service import ApiService
        python_files_in_root = find_python_files_in_path()
        # 서비스 파일(root아래)들을 import
        for python_file in python_files_in_root:
            importlib.import_module(python_file)

        # Already registered services
        self.unregister_service_names = [
            service.name
            for service in await self.services
        ]

        # import 되었으므로 AbstractService의 subclasses로 접근 가능
        for service in get_all_subclasses(AbstractService):
            if service.depth < 2:
                continue
            service_name = service.__name__
            await self.db.create_service_meta(service_name=service_name, rpc_funcs=service.rpc_funcs)
            self.registered_services.append(service)
            if service_name in self.unregister_service_names:
                self.unregister_service_names.remove(service_name)

        if self.unregister_service_names:
            print(
                'Warning: Unregistered services found, check the service name.. or remove the service db..')
            # print(self.unregister_service_names)

    def validate_service(self, service_name: str) -> bool:
        if service_name in self.unregister_service_names:
            return False
        return True

    async def register_service(self, temporary_service_id: str):
        # service_id = f"{self.__class__.__name__}_{timeit.timeit()}"
        service_name, _ = temporary_service_id.split('_')
        service_meta = await self.db.get_service_meta(service_name)
        new_service = await self.db.create_service(service_meta)

        self.health_map[
            new_service.id
        ] = new_service.created_at.timestamp()

        return new_service.id

    async def unregister_service(
        self,
        service_id: int,
    ):
        # cli 등에서 실행 가능
        await self.db.update_service(service_id, ServiceState.INACTIVE)
        await self.redis_broker.broadcast(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterSystemMessage(
                type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
                data=service_id
            ).encode()
        )
        self.health_map.pop(service_id, None)

    async def start_service(self, service_name: str):
        # 중복 실행 막기
        # ...
        # 실행
        # 서비스 클래스 이름(eg)AchivementService)으로 서비스 찾기
        service = next(
            (service for service in self.registered_services if service.__name__ == service_name), None)
        if service is None:
            raise Exception('실행하려는 서비스가 등록되지 않았습니다.')
        command = get_running_command(service.__module__, service_name)
        proc = await asyncio.create_subprocess_shell(
            f'{sys.executable} -c "{command}"',
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        _, error = await proc.communicate()
        error and print('error: ', error.decode())

    async def stop_services(self, service_ids: list[int]):
        for service_id in service_ids:
            service = await self.db.get_service(service_id)
            if service and service.state == ServiceState.ACTIVE:
                target = service.service_meta.name.lower() + '_' + 'service_handler'
                await self.redis_broker.send_message(
                    target,
                    ArbiterSystemMessage(
                        type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
                    ).encode(),
                    0
                )

    async def health_check_func(self):
        while not self.system_task.done():
            current_time = time.time()
            removed_service_ids = []
            for service_id, last_time in self.health_map.items():
                if current_time - last_time > ARBITER_SERVICE_TIMEOUT:
                    removed_service_ids.append(service_id)
            for removed_service_id in removed_service_ids:
                # 응답이 없는 테스크 이다, 어떻게 처리해야 할까?
                # 경고  몇 번후 다른 서비스들에게 공지해볼까
                await self.unregister_service(removed_service_id)

            await asyncio.sleep(1)
        # 마찬가지로 현재는 사용하지 않는다.
        # update last health check time
        # async with PrismaClientWrapper.get_instance().batch_() as batcher:
        #     for service_id, last_time in self.health_map.items():
        #         batcher.serviceregistry.update(
        #             where={
        #                 'id': service_id
        #             },
        #             data={
        #                 'updated_at': datetime.fromtimestamp(last_time)
        #             })

    async def system_task_func(self):
        while True:
            request_json = await self.redis_broker.client.blpop(
                ARBITER_SYSTEM_QUEUE, timeout=ARBITER_SYSTEM_TIMEOUT)
            if request_json:
                try:
                    message = ArbiterMessage.decode(request_json[1])
                    requset_message = ArbiterSystemRequestMessage.decode(
                        message.data)
                    from_service_id = requset_message.from_id
                    response = None
                    match requset_message.type:
                        case ArbiterMessageType.PING:
                            if from_service_id in self.health_map:
                                self.health_map[from_service_id] = time.time()
                                response = ArbiterSystemMessage(
                                    type=ArbiterMessageType.PONG
                                )
                        case ArbiterMessageType.ARBITER_SERVICE_REGISTER:
                            if registed_service_id := await self.register_service(from_service_id):
                                response = ArbiterSystemMessage(
                                    type=ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK,
                                    data=registed_service_id
                                )
                        case ArbiterMessageType.ARBITER_SERVICE_UNREGISTER:
                            await self.unregister_service(from_service_id)
                            response = ArbiterSystemMessage(
                                type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER_ACK,
                            )
                        case ArbiterMessageType.SHUTDOWN:
                            if self.shutdown_code == from_service_id:
                                break
                except Exception as e:
                    print('Error: ', e)
                    response = ArbiterSystemMessage(
                        message_type=ArbiterMessageType.ERROR,
                        data=str(e)
                    )
                response and await self.redis_broker.notify(
                    message.id,
                    response.encode()
                )
            else:
                # Timeout 발생
                # Arbiter 상태 확인
                # Arbiter Shutdown
                print('Timeout break, Arbiter Shutdown')
                break


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))
