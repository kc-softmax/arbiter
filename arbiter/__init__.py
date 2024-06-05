import asyncio
import sys
import atexit
import signal
import os
import importlib
import asyncio
import time
from arbiter.broker import RedisBroker
from arbiter.database import PrismaClientWrapper
from arbiter.service import AbstractService
from arbiter.api.api_service import ApiService
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

    def __init__(self):
        self.redis_broker: RedisBroker = None
        self.system_task: asyncio.Task = None
        # TODO temporary use, before using database
        self.pids: dict[str, int] = {}  # THINK we need this?
        self.registered_services: list[type[AbstractService]] = []
        self.services_number: dict[int, str] = {}
        ###########################################
        self.health_check_task: asyncio.Task = None
        self.health_map: dict[str, int] = {}

    async def start(self, **kwargs):
        atexit.register(self.cleanup)
        self.register_services_meta()
        await PrismaClientWrapper.connect()
        self.redis_broker = RedisBroker()
        await self.redis_broker.connect()
        self.system_task = asyncio.create_task(self.system_task_func())
        self.health_check_task = asyncio.create_task(self.health_check_func())

        for service in self.registered_services:
            asyncio.create_task(self.start_service(service.__name__))

        await self.system_task  # temp
        await self.shutdown()

    async def shutdown(self):
        await self.redis_broker.publish(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterMessage(
                from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                message_type=ArbiterMessageType.SHUTDOWN,
            ).encode()
        )
        await PrismaClientWrapper.disconnect()
        await self.redis_broker.disconnect()
        if self.system_task:
            self.system_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()

    def register_services_meta(self):
        python_files_in_root = find_python_files_in_path()
        # 서비스 파일(root아래)들을 import
        for python_file in python_files_in_root:
            importlib.import_module(python_file)
        # import 되었으므로 AbstractService의 subclasses로 접근 가능
        for idx, service in enumerate(AbstractService.__subclasses__(), start=1):
            self.services_number[idx] = service.__name__
            self.registered_services.append(service)

    async def register_service(self, temporary_service_id: str):
        # parse service_id
        # service_id = f"{self.__class__.__name__}_{timeit.timeit()}"
        service_name, service_id = temporary_service_id.split('_')
        self.health_map[service_id] = time.time()
        return service_id

    async def unregister_service(self, service_id: str) -> bool:
        print(f"unregister_service: {service_id}")
        if not self.health_map.pop(service_id, None):
            return False
        await self.redis_broker.publish(
            ARBITER_SYSTEM_CHANNEL,
            ArbiterMessage(
                from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                message_type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER,
                data=service_id
            ).encode()
        )
        return True
    # cli 등에서 실행 가능

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
        print(error.decode())

    def stop_service(self, service_name: str):
        pid = self.pids.pop(service_name)
        os.kill(pid, signal.SIGTERM)

    async def health_check_func(self):
        while True:
            current_time = time.time()
            removed_service_ids = []
            for service_id, last_time in self.health_map.items():
                if current_time - last_time > ARBITER_SERVICE_TIMEOUT:
                    removed_service_ids.append(service_id)
            for removed_service_id in removed_service_ids:
                await self.unregister_service(removed_service_id)

            await asyncio.sleep(1)

    async def system_task_func(self):
        while True:
            request_json = await self.redis_broker.client.blpop(
                ARBITER_SYSTEM_QUEUE, timeout=ARBITER_SYSTEM_TIMEOUT)
            if request_json:
                try:
                    message = ArbiterMessage.decode(request_json[1])
                    from_service_id = message.from_service_id
                    response = None
                    # 요청 처리
                    match message.message_type:
                        case ArbiterMessageType.PING:
                            self.health_map[from_service_id] = time.time()
                            response = ArbiterMessage(
                                from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                                message_type=ArbiterMessageType.PONG
                            )
                        case ArbiterMessageType.ARBITER_SERVICE_REGISTER:
                            registed_service_id = await self.register_service(from_service_id)
                            response = ArbiterMessage(
                                from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                                message_type=ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK,
                                data=registed_service_id
                            )
                        case ArbiterMessageType.ARBITER_SERVICE_UNREGISTER:
                            if await self.unregister_service(from_service_id):
                                response = ArbiterMessage(
                                    from_service_id=ARBITER_SYSTEM_SERVICE_ID,
                                    message_type=ArbiterMessageType.ARBITER_SERVICE_UNREGISTER_ACK,
                                )
                except Exception as e:
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

    def cleanup(self):
        print("Cleaning up resources...")
