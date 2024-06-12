import asyncio
import sys
import atexit
import signal
import os
import importlib
import asyncio
import time
from datetime import datetime
from prisma.models import Service, ServiceRegistry
from arbiter.broker import RedisBroker
from arbiter.database import PrismaClientWrapper
from arbiter.service import AbstractService
from arbiter.constants import (
    ARBITER_SERVICE_TIMEOUT,
    ARBITER_SYSTEM_TIMEOUT,
    ARBITER_SYSTEM_SERVICE_ID,
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_SYSTEM_QUEUE,
    ArbiterMessage,
    ArbiterMessageType
)
from arbiter.utils import (
    find_python_files_in_path,
    get_running_command
)


class Arbiter:
    # #THINK meta class를 통해 모든 broker를 관리한다...?

    @property
    async def services(self) -> list[Service]:
        return await Service.prisma().find_many()

    @property
    async def active_services(self) -> list[ServiceRegistry]:
        return await ServiceRegistry.prisma().find_many(
            where={
                'state': 'active'
            },
            include={
                'service': True})

    def __init__(self):
        self.redis_broker: RedisBroker = None
        self.system_task: asyncio.Task = None
        self.current_services: list[Service] = []
        self.registered_services: list[type[AbstractService]] = []
        self.unregister_service_names: list[str] = []
        self.health_check_task: asyncio.Task = None
        # 동기화 한다.
        self.health_map: dict[int, int] = {}

    async def clear(self):
        if self.system_task:
            self.system_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        await PrismaClientWrapper.disconnect()
        await self.redis_broker.disconnect()

    async def start(self, **kwargs):
        await PrismaClientWrapper.connect()
        await self.register_services_meta()

        self.redis_broker = RedisBroker()
        await self.redis_broker.connect()

        # loop = asyncio.new_event_loop()
        self.system_task = asyncio.create_task(self.system_task_func())

        self.health_check_task = asyncio.create_task(self.health_check_func())

        if active_services := await ServiceRegistry.prisma().find_many(where={
            'state': 'active'
        }):
            for active_service in active_services:
                self.health_map[active_service.id] = active_service.updated_at.timestamp(
                )

        for service in self.registered_services:
            asyncio.create_task(self.start_service(service.__name__))

        await self.health_check_task

        # broker를 통해 main이 shutdown 되었다고 알린다.
        await self.redis_broker.publish(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterMessage(
                ARBITER_SYSTEM_SERVICE_ID, ArbiterMessageType.SHUTDOWN).encode())
        await self.clear()

    async def stop(self):
        # api, arbiter main task를 제외한 나머지 서비스들을 중단한다.
        # 다른 서비스 종료방법 1
        # self.health_map.clear() 하면 main health_check_func은 올바르게 동작하지 않지만
        # 곧 종료될 것이므로 신경쓰지 않는다. 하지만 각 서비스들에의 health_check_func에서 예외가 발생하여 종료될 것이다.
        # self.health_map.clear()
        active_service_ids = [
            active_service.id
            for active_service in await ServiceRegistry.prisma().find_many(where={
                'state': 'active'
            })]
        await self.stop_services(active_service_ids)

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
        stop_task = asyncio.create_task(self.stop())
        await stop_task
        print('all services are stopped')
        # cancel system task nataurally
        await self.redis_broker.send_request(
            ARBITER_SYSTEM_QUEUE,
            ArbiterMessage(ARBITER_SYSTEM_SERVICE_ID, ArbiterMessageType.SHUTDOWN))
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
        for service in AbstractService.__subclasses__():
            service_name = service.__name__
            if not await Service.prisma().find_unique(where={
                'name': service_name
            }):
                await Service.prisma().create(data={'name': service_name})
            self.registered_services.append(service)
            if service_name in self.unregister_service_names:
                self.unregister_service_names.remove(service_name)

        if self.unregister_service_names:
            print(
                'Warning: Unregistered services found, check the service name.. or remove the service db..')
            print(self.unregister_service_names)

    def validate_service(self, service_name: str) -> bool:
        if service_name in self.unregister_service_names:
            return False
        return True

    async def register_service(self, temporary_service_id: str):
        # service_id = f"{self.__class__.__name__}_{timeit.timeit()}"
        service_name, _ = temporary_service_id.split('_')
        if service := await Service.prisma().find_unique(where={
            'name': service_name
        }):
            new_service_registry = await ServiceRegistry.prisma().create(
                data={'service_id': service.id})
            self.health_map[
                new_service_registry.id
            ] = new_service_registry.created_at.timestamp()
            return new_service_registry.id
        else:
            return None

    async def unregister_service(
        self,
        service_registry_id: int,
        state: str = 'inactive',
    ):
        # cli 등에서 실행 가능
        await ServiceRegistry.prisma().update(
            where={'id': service_registry_id},
            data={'state': state, 'updated_at': datetime.now()})
        await self.redis_broker.publish(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterMessage(
                from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                message_type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
                data=service_registry_id
            ).encode()
        )
        self.health_map.pop(service_registry_id, None)

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
        if not service_ids:
            return
        await self.redis_broker.publish(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterMessage(
                from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                message_type=ArbiterMessageType.ARBITER_SERVICE_STOP,
                data=service_ids
            ).encode()
        )
        start_time = time.time()
        while True:
            if time.time() - start_time > 10:
                # 서비스가 종료되지 않았기 때문에 확인하는 메세지를 보내야한다.
                # 경고메세지 출력
                print('Some services are not stopped yet...')
                break

            if not await ServiceRegistry.prisma().find_many(where={
                'id': {
                    'in': service_ids
                },
                'state': 'active'
            }):
                break

            await asyncio.sleep(1)

        # 종료 메세지가 오지 않은 서비스들에 대한 처리
        for remove_service in await ServiceRegistry.prisma().find_many(where={
            'id': {
                'in': service_ids
            },
            'state': 'active'
        }):
            await self.unregister_service(remove_service.id, 'stop_error')

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
                await self.unregister_service(removed_service_id, 'health_failed')

            await asyncio.sleep(1)
        # update last health check time
        async with PrismaClientWrapper.get_instance().batch_() as batcher:
            for service_id, last_time in self.health_map.items():
                batcher.serviceregistry.update(
                    where={
                        'id': service_id
                    },
                    data={
                        'updated_at': datetime.fromtimestamp(last_time)
                    })

    async def system_task_func(self):
        while True:
            request_json = await self.redis_broker.client.blpop(
                ARBITER_SYSTEM_QUEUE, timeout=ARBITER_SYSTEM_TIMEOUT)
            if request_json:
                try:
                    message = ArbiterMessage.decode(request_json[1])
                    from_service_id = message.from_service_id
                    response = None
                    match message.message_type:
                        case ArbiterMessageType.PING:
                            if from_service_id in self.health_map:
                                self.health_map[from_service_id] = time.time()
                                response = ArbiterMessage(
                                    from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                                    message_type=ArbiterMessageType.PONG
                                )
                        case ArbiterMessageType.ARBITER_SERVICE_REGISTER:
                            if registed_service_id := await self.register_service(from_service_id):
                                response = ArbiterMessage(
                                    from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                                    message_type=ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK,
                                    data=registed_service_id
                                )
                        case ArbiterMessageType.ARBITER_SERVICE_UNREGISTER:
                            await self.unregister_service(from_service_id)
                            response = ArbiterMessage(
                                from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                                message_type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER_ACK,
                            )
                        case ArbiterMessageType.SHUTDOWN:
                            if from_service_id == ARBITER_SYSTEM_SERVICE_ID:
                                break
                except Exception as e:
                    print('Error: ', e)
                    response = ArbiterMessage(
                        from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                        message_type=ArbiterMessageType.ERROR,
                        payload=str(e)
                    )
                response and await self.redis_broker.client.set(
                    from_service_id,
                    response.encode()
                )
            else:
                # Timeout 발생
                # Arbiter 상태 확인
                # Arbiter Shutdown
                print('Timeout break, Arbiter Shutdown')
                break


arbiter = Arbiter()
# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))
