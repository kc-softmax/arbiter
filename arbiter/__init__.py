from __future__ import annotations
import asyncio
import uuid
import importlib
import time
import json
import inspect
import pickle
from pydantic import BaseModel
from contextlib import asynccontextmanager
from warnings import warn
from typing import AsyncGenerator, TypeVar, Generic, get_type_hints
from arbiter.broker import RedisBroker
from arbiter.database import Database
from arbiter.database.model import (
    Service,
    ServiceMeta, 
    Node,
    TaskFunction,
)
from arbiter.service import AbstractService
from arbiter.constants import (
    ArbiterMessage,
    ArbiterBroadcastMessage,
    WARP_IN_TIMEOUT,
    ARBITER_SERVICE_PENDING_TIMEOUT,
    ARBITER_SERVICE_ACTIVE_TIMEOUT,
    ARBITER_SYSTEM_TIMEOUT,
    ARBITER_SERVICE_SHUTDOWN_TIMEOUT,
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_API_CHANNEL,
    ALLOWED_TYPE,
    AUTH_PARAMETER,
)
from arbiter.constants.enums import (
    WarpInTaskResult,
    ArbiterShutdownTaskResult,
    ArbiterMessageType,
    WarpInPhase,
    ServiceState
)
from arbiter.utils import (
    extract_annotation,
    find_python_files_in_path,
    get_all_subclasses,
    to_snake_case,

)
T = TypeVar('T')


class TypedQueue(asyncio.Queue, Generic[T]):
    async def get(self) -> T:
        return await super().get()


class Arbiter:
    
    @property
    async def services(self) -> list[ServiceMeta]:
        return await self.db.search_data(ServiceMeta)

    @property
    async def active_services(self) -> list[Service]:
        return await self.db.search_data(Service, state=ServiceState.ACTIVE)

    @property
    def is_replica(self) -> bool:
        return not self.node.is_master

    def __init__(self, name: str):
        self.name = name
        self.node: Node = None
        self.broker: RedisBroker = None
        self.system_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.pending_service_queue: TypedQueue[Service] = TypedQueue()
        # 동기화 한다.
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown_queue: asyncio.Queue = asyncio.Queue()
        self.db = Database.get_db()
        self.shutdown_flag = False

    async def clear(self):
        if self.node and not self.is_replica:
            # 임시코드 master node가 삭제하면 전부 삭제해버린다.
            await self.db.initialize()
        if self.system_task:
            self.system_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.db:
            await self.db.disconnect()
        if self.broker:
            await self.broker.disconnect()

    async def register_service(self, service_id: str):
        if service := await self.db.get_data(Service, service_id):
            await self.db.update_data(
                service,
                state=ServiceState.ACTIVE
            )
            # add route in arbiter
            service_meta = service.service_meta
            if routing_functions := await self.db.search_data(TaskFunction, service_meta=service_meta):
                for routing_function in routing_functions:
                    # add route in arbiter
                    await self.broker.broadcast(
                        ARBITER_API_CHANNEL, 
                        routing_function.model_dump_json())
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
        try:
            await self.broker.broadcast(
                ARBITER_SYSTEM_CHANNEL,
                ArbiterBroadcastMessage(
                    type=ArbiterMessageType.MASTER_SHUTDOWN).model_dump_json()
            )
            if replica_nodes := await self.db.search_data(Node, name=self.name, is_master=False):
                for replica_node in replica_nodes:
                    await self.broker.send_message(
                        replica_node.unique_id,
                        ArbiterMessage(
                            data=ArbiterMessageType.SHUTDOWN,
                            sender_id=self.node.shutdown_code))
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
                await asyncio.sleep(0.3)
        except Exception as e:
            print('Error: ', e)
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
            self.node.unique_id,
            ArbiterMessage(
                data=ArbiterMessageType.SHUTDOWN,
                sender_id=self.node.shutdown_code, 
                response=False))
        self.shutdown_flag = True
        await self.system_task
        await self.health_check_task

    async def _setup_initial_task(self):
        async def check_initial_services(timeout: int) -> list[Service]:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if not await self.db.search_data(Service, state=ServiceState.PENDING):
                    return []
                await asyncio.sleep(0.5)
            return await self.db.search_data(Service, state=ServiceState.PENDING)
        # api 와 함께라면 api 부터 검사해야 한다.
        if pending_services := await check_initial_services(ARBITER_SERVICE_PENDING_TIMEOUT):
            # failed to start all services
            # 실패한 서비스들을 어떻게 처리할 것인가? 쓰는사람에게 맡긴다.
            pending_service_names = ', '.join(
                [service.service_meta.name for service in pending_services])
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, pending_service_names))
        else:
            await self._warp_in_queue.put(
                (WarpInTaskResult.SUCCESS, None))
        
    async def warp_in(self, phase: WarpInPhase) -> AsyncGenerator[tuple[WarpInTaskResult, str], None]:
        while True:
            try:
                message = await asyncio.wait_for(
                    self._warp_in_queue.get(),
                    WARP_IN_TIMEOUT
                )
                if message is None:
                    break
                yield message
            except asyncio.TimeoutError:
                yield (WarpInTaskResult.FAIL, f"Warp In Timeout in {phase.name} phase.")

    @asynccontextmanager
    async def start(self, config: dict[str, str]={}) -> AsyncGenerator[Arbiter, Exception]:
        try:
            await self.db.connect()
            await self.db.initialize()
            node_data = dict(
                name=self.name,
                unique_id=uuid.uuid4().hex,
                shutdown_code=uuid.uuid4().hex,
                is_master=True,
                ip_address="",
            )
            if previous_nodes := await self.db.search_data(Node, name=self.name):
                # find master node in previous nodes
                if master_node := next((node for node in previous_nodes if node.is_master), None):
                    node_data.update(is_master=False)
                    await self._warp_in_queue.put(
                        (WarpInTaskResult.IS_REPLICA, f"{master_node.unique_id}'s Replica Node is created")
                    )
                else:
                    raise ValueError('Master Node is not found, but there are nodes with the same name.')
            else:
                await self._warp_in_queue.put(
                    (WarpInTaskResult.IS_MASTER, 'Master Node is created')
                )
        except Exception as e:
            await self.db.initialize()
            await self.clear()
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, e)
            )
            await self._warp_in_queue.put(None)
            yield self
            return
        await self._warp_in_queue.put(None)
        self.node = await self.db.create_data(
            Node,
            **node_data
        )  # TODO Change
        self.broker = RedisBroker()
        await self.broker.connect()
        try:
            python_files_in_root = find_python_files_in_path()
            # 프로젝트 root아래 있는 service.py 파일들을 import한다.
            for python_file in python_files_in_root:
                importlib.import_module(python_file)

            # import 되었으므로 AbstractService의 subclasses로 접근 가능
            service_classes = get_all_subclasses(AbstractService)
            for service_class in service_classes:
                assert issubclass(service_class, AbstractService)
                if service_class.depth < 2:
                    continue
                
                service_meta = await self.db.create_data(
                    ServiceMeta,
                    name=service_class.__name__,
                    module_name=service_class.__module__)
                
                if tasks := service_class.tasks:
                    """
                        model의 parameter를 확인할 수 있는 정보
                        pydantic model의 type을 dict로 저장해야 한다.
                    """
                    for task in tasks:
                        # task는 function 내용이다, 즉 response model이 없다
                        try:
                            if not getattr(task, 'routing', False):
                                continue
                            signature = inspect.signature(task)
                            # deprecated, because of using dynamic pydantic model
                            # Print the parameters of the function
                            # check if the first argument is User instance
                            # parameters = [
                            #     (param.name, extract_annotation(param))
                            #     for param in signature.parameters.values()
                            #     if param.name != 'self'
                            # ]

                            data = dict(
                                name=task.__name__,
                                queue_name=f"{to_snake_case(service_meta.name)}_{task.__name__}",
                                service_meta=service_meta,
                                auth=getattr(task, 'auth', False),
                                method=getattr(task, 'method', None),
                                connection=getattr(task, 'connection', None),
                                communication_type=getattr(task, 'communication_type', None),
                            )
                            request_models_params: list = []
                            response_model_params = None
                            
                            for param in signature.parameters.values():
                                annotation = param.annotation
                                if param.name == 'self':
                                    continue
                                if param.name == AUTH_PARAMETER:
                                    continue
                                name = param.name
                                annotation = param.annotation
                                
                                # 타입 힌트를 가져와서 허용된 타입 중 하나인지 확인
                                if not isinstance(annotation, type):
                                    annotation = get_type_hints(signature).get(param.name, None)
                                
                                assert annotation is not None, f"Parameter {param.name} should have a type annotation"
                                assert isinstance(annotation, type), f"Parameter {param.name} annotation must be a type"
                                assert issubclass(annotation, ALLOWED_TYPE), f"Parameter {param.name} should be one of {ALLOWED_TYPE}"
                                
                                if issubclass(annotation, BaseModel):
                                    request_model_params = annotation.model_json_schema()
                                else:
                                    request_model_params = annotation.__name__
                                
                                request_models_params.append((name, request_model_params))

                            if response_model := getattr(task, 'response_model', None):
                                assert isinstance(response_model, type), f"{response_model} annotation must be a type"
                                assert issubclass(response_model, ALLOWED_TYPE), f"{response_model} should be one of {ALLOWED_TYPE}"
                                if issubclass(response_model, BaseModel):
                                    response_model_params = response_model.model_json_schema()
                                else:
                                    response_model_params = response_model.__name__
                                    
                            data.update(
                                request_models=json.dumps(request_models_params),
                                response_model=json.dumps(response_model_params) if response_model_params else None,
                            )
                            await self.db.create_data(TaskFunction, **data)
                        except Exception as e:
                            print('ex: ', e)
                        
                if service_class.auto_start:
                    for _ in range(service_class.initial_processes):
                        await self.pending_service_queue.put(
                            await self.db.create_data(
                                Service,
                                name=uuid.uuid4().hex,
                                state=ServiceState.PENDING,
                                service_meta=service_meta
                            )
                        )

        except Exception as e:
            await self.clear()
            yield e
            return
        self.system_task = asyncio.create_task(self.system_task_func())

        # TODO 확인해야 한다, 서비스가 정상적으로 켜진건지 할 수  있다면
        # 만약 켜지지 않았다면, new_service 객체를 바탕으로 조정해야 한다.
        # process = asyncio.create_task(self.start_service(new_service))
        # processes.append(process)
        asyncio.create_task(self._setup_initial_task())

        self.health_check_task = asyncio.create_task(
            self.health_check_func())

        yield self

        await self.clear()

    async def stop_services(self, service_ids: list[int]):
        for service_id in service_ids:
            service = await self.db.get_data(Service, service_id)
            if service and service.state == ServiceState.ACTIVE:
                target = f"{to_snake_case(service.service_meta.name)}_listener"
                print('stop service not working')
                # await self.broker.send_message(
                #     target,
                    
                #     ArbiterMessageType.ARBITER_SERVICE_UNREGISTER)

    async def health_check_func(self):
        while not self.system_task.done():
            current_time = time.time()
            description = ''
            removed_services = []
            pending_or_active_services = await self.db.search_data(
                Service, state=ServiceState.PENDING)
            pending_or_active_services.extend(
                await self.db.search_data(Service, state=ServiceState.ACTIVE))            
            for service in pending_or_active_services:
                elapsed_time = current_time - service.updated_at.timestamp()
                if service.state == ServiceState.ACTIVE:
                    description = 'Service is not responding.'
                    timeout = ARBITER_SERVICE_ACTIVE_TIMEOUT
                elif service.state == ServiceState.PENDING:
                    description = f'Service is not started within {elapsed_time} seconds.'
                    timeout = ARBITER_SERVICE_PENDING_TIMEOUT
                else:
                    raise ValueError('Invalid Service State')
                if elapsed_time > timeout:
                    removed_services.append((service, description))

            for removed_service in removed_services:
                await self.unregister_service(*removed_service)

            await asyncio.sleep(0.5)

    async def system_task_func(self):
        async for message in self.broker.listen(
            self.node.unique_id, 
            ARBITER_SYSTEM_TIMEOUT
        ):
            try:
                sender_id = message.sender_id
                message_type = ArbiterMessageType(int(message.data))
                response: ArbiterMessageType = None
                match message_type:
                    case ArbiterMessageType.API_REGISTER:
                        await self._warp_in_queue.put((
                            WarpInTaskResult.API_REGISTER_SUCCESS,
                            sender_id))
                    case ArbiterMessageType.API_UNREGISTER:
                        await self._warp_in_queue.put((
                            WarpInTaskResult.API_REGISTER_SUCCESS,
                            sender_id))
                    case ArbiterMessageType.PING:
                        # health check의 경우 한번에 모아서 업데이트 하는 경우를 생각해봐야한다.
                        if service := await self.db.get_data(Service, sender_id):
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
                                response = ArbiterMessageType.PONG
                    case ArbiterMessageType.ARBITER_SERVICE_REGISTER:
                        if await self.register_service(sender_id):
                            response = ArbiterMessageType.ARBITER_SERVICE_REGISTER_ACK
                    case ArbiterMessageType.ARBITER_SERVICE_UNREGISTER:
                        if unregistered_service := await self.db.get_data(Service, sender_id):
                            await self.unregister_service(unregistered_service)
                            response = ArbiterMessageType.ARBITER_SERVICE_UNREGISTER_ACK
                    case ArbiterMessageType.SHUTDOWN:
                        if self.node.shutdown_code == sender_id:
                            break
            except Exception as e:
                print('Error: ', e)
                print('Message: ', message_type, sender_id)
                response = ArbiterMessageType.ERROR
            finally:
                if response and message.response:
                    await self.broker.push_message(
                        message.id,
                        response.value
                    )

        if not self.shutdown_flag:
            # pending_service_queue에 None을 넣어서
            # cli의 종료를 유도하여 shutdown_task를 실행한다.
            await self.pending_service_queue.put(None)


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))
