from __future__ import annotations
import asyncio
import uuid
import importlib
import time
import json
from inspect import Parameter
from pydantic import BaseModel
from contextlib import asynccontextmanager
from warnings import warn
from typing import (
    AsyncGenerator,
    TypeVar, 
    Generic,
    Union, 
    get_origin,
    get_args, 
    List
)
from arbiter import Arbiter
from arbiter.database.model import (
    Service,
    ServiceMeta, 
    Node,
    HttpTaskFunction,
    StreamTaskFunction
)
from arbiter.service import AbstractService
from arbiter.constants import (
    ArbiterTypedData,
    WARP_IN_TIMEOUT,
    ARBITER_SERVICE_PENDING_TIMEOUT,
    ARBITER_SERVICE_ACTIVE_TIMEOUT,
    ARBITER_SYSTEM_TIMEOUT,
    ARBITER_SERVICE_SHUTDOWN_TIMEOUT,
    ARBITER_SYSTEM_CHANNEL,
    ARBITER_API_CHANNEL)
from arbiter.constants.enums import (
    WarpInTaskResult,
    ArbiterShutdownTaskResult,
    ArbiterDataType,
    WarpInPhase,
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


class ArbiterRunner:
    
    @property
    async def services(self) -> list[ServiceMeta]:
        return await self.arbiter.search_data(ServiceMeta)

    @property
    async def active_services(self) -> list[Service]:
        return await self.arbiter.search_data(Service, state=ServiceState.ACTIVE, node_id=self.node.id)

    @property
    def is_replica(self) -> bool:
        return not self.node.is_master

    def __init__(self, name: str):
        self.name = name
        self.node: Node = None
        # arbiter와 database merge
        self.arbiter: Arbiter = Arbiter(name)
        # self.db = Database.get_db(name)
        self.system_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.pending_service_queue: TypedQueue[Service] = TypedQueue()
        # 동기화 한다.
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown_queue: asyncio.Queue = asyncio.Queue()
        self.shutdown_flag = False

    async def clear(self):
        if self.node:
            await self.arbiter.update_data(
                self.node,
                state=ServiceState.INACTIVE
            )
        if self.system_task:
            self.system_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        # if self.db:
        #     await self.db.disconnect()
        if self.arbiter:
            await self.arbiter.disconnect()

    async def register_service(self, service_id: str):
        if service := await self.arbiter.get_data(Service, service_id):
            await self.arbiter.update_data(
                service,
                state=ServiceState.ACTIVE
            )
            # add route in arbiter
            service_meta = service.service_meta
            if http_task_functions := await self.arbiter.search_data(HttpTaskFunction, service_meta=service_meta):
                for http_task_function in http_task_functions:
                    # add route in arbiter
                    await self.arbiter.broadcast(
                        ARBITER_API_CHANNEL, 
                        http_task_function.model_dump_json())
                    
            if stream_task_functions := await self.arbiter.search_data(StreamTaskFunction, service_meta=service_meta):
                for stream_task_function in stream_task_functions:
                    # add route in arbiter
                    await self.arbiter.broadcast(
                        ARBITER_API_CHANNEL, 
                        stream_task_function.model_dump_json())                    
            return True
        return False

    async def unregister_service(
        self,
        service: Service,
        description: str = None
    ):
        # cli 등에서 실행 가능
        await self.arbiter.update_data(
            service,
            state=ServiceState.INACTIVE,
            description=description,
        )

    async def _setup_shutdown_task(self):
        try:
            if not self.is_replica:
                await self.arbiter.broadcast(
                    topic=ARBITER_SYSTEM_CHANNEL,
                    message=ArbiterTypedData(
                        type=ArbiterDataType.MASTER_SHUTDOWN,
                        data=self.node.unique_id
                    ).model_dump_json()
                )
                if replica_nodes := await self.arbiter.search_data(
                    Node,
                    state=ServiceState.ACTIVE,
                    name=self.name, 
                    is_master=False
                ):
                    for replica_node in replica_nodes:
                        await self.arbiter.send_message(
                            receiver_id=replica_node.unique_id,
                            data=ArbiterTypedData(
                                type=ArbiterDataType.SHUTDOWN,
                                data=replica_node.shutdown_code
                            ).model_dump_json()
                        )
            else:
                await self.arbiter.broadcast(
                    topic=ARBITER_SYSTEM_CHANNEL,
                    message=ArbiterTypedData(
                        type=ArbiterDataType.SHUTDOWN,
                        data=self.node.unique_id
                    ).model_dump_json()
                )
            start_time = time.time()
            if not self.system_task.done():
                while True:
                    try:
                        # system_task 가 먼저 종료되었다면, 확인할 수 없다.
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
                    except Exception as e:
                        print(e)
                    await asyncio.sleep(0.3)
            else:
                await self._shutdown_queue.put(
                    (ArbiterShutdownTaskResult.WARNING, "System Task is already done.")
                )                
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
        try:
            self.shutdown_flag = True
            await self.pending_service_queue.put(None)
            asyncio.create_task(self._setup_shutdown_task())
            while True:
                message = await self._shutdown_queue.get()
                if message == None:
                    break
                yield message
            await self.arbiter.send_message(
                receiver_id=self.node.unique_id,
                data=ArbiterTypedData(
                    type=ArbiterDataType.SHUTDOWN,
                    data=self.node.shutdown_code
                ).model_dump_json()
            )
            await self.system_task
            await self.health_check_task
        except Exception as e:
            print('Error in shutdown: ', e)

    async def _setup_initial_task(self):
        async def check_initial_services(timeout: int) -> list[Service]:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if not await self.arbiter.search_data(
                    Service,
                    state=ServiceState.PENDING,
                    node_id=self.node.id):
                    return []
                await asyncio.sleep(0.5)
            return await self.arbiter.search_data(
                Service,
                state=ServiceState.PENDING,
                node_id=self.node.id)
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
    async def start(self, config: dict[str, str]={}) -> AsyncGenerator[ArbiterRunner, Exception]:
        try:
            await self.arbiter.connect()
            node_data = dict(
                name=self.name,
                unique_id=uuid.uuid4().hex,
                shutdown_code=uuid.uuid4().hex,
                is_master=True,
                ip_address="",
            )
            if previous_nodes := await self.arbiter.search_data(Node, name=self.name, state=ServiceState.ACTIVE):
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
            await self.clear()
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, e)
            )
            await self._warp_in_queue.put(None)
            yield self
            return
        self.node = await self.arbiter.create_data(
            Node,
            state=ServiceState.ACTIVE,
            **node_data
        )  # TODO Change
        await self._warp_in_queue.put(None)
        await self.arbiter.connect()
        try:
            python_files_in_root = find_python_files_in_path(
                is_master=self.node.is_master
            )
            
            try:
                # 프로젝트 root아래 있는 service.py 파일들을 import한다.
                for python_file in python_files_in_root:
                    importlib.import_module(python_file)
            except Exception as e:
                print('importlib error in : ', e)
            # import 되었으므로 AbstractService의 subclasses로 접근 가능
            service_classes = get_all_subclasses(AbstractService)
            for service_class in service_classes:
                assert issubclass(service_class, AbstractService)
                if service_class.depth < 2:
                    continue
                service_meta = await self.arbiter.create_data(
                    ServiceMeta,
                    node_id=self.node.id,
                    name=service_class.__name__,
                    module_name=service_class.__module__)
                
                if tasks := service_class.tasks:
                    try:
                        for task in tasks:
                            if not getattr(task, 'routing', False):
                                continue
                            task_name = task.__name__
                            task_queue = f"{to_snake_case(service_meta.name)}_{task.__name__}"
                            data = dict(
                                service_meta=service_meta,
                                name=task_name,
                                auth=getattr(task, 'auth', False),
                                task_queue=task_queue,
                            )
                            task_function_cls = None
                            if getattr(task, 'method', None):
                                # httpTask
                                data.update(
                                    method=getattr(task, 'method', None),
                                )
                                task_function_cls = HttpTaskFunction
                            if getattr(task, 'communication_type', None):
                                # stream task
                                data.update(
                                    connection=getattr(task, 'connection', None),
                                    communication_type=getattr(task, 'communication_type', None),
                                    num_of_channels=getattr(task, 'num_of_channels', 1),
                                )
                                task_function_cls = StreamTaskFunction

                            assert task_function_cls is not None, 'Task Function Class is not found'
                            task_params = getattr(task, 'task_params', {})
                            assert task_params is not None, 'Task Params is not found'
                            task_response_type = getattr(task, 'response_type', None)
                            task_has_response = getattr(task, 'has_response', True)
                            # response type 이 있을경우 has_response는 True여야 한다.
                            assert task_response_type is None or task_has_response, 'Task has response but response type is not found'
                            
                            flatten_params = {}
                            flatten_response = ''
                            
                            for param_name, parameter in task_params.items():
                                assert isinstance(parameter, Parameter), f"{param_name} is not a parameter"
                                annotation = parameter.annotation
                                param_model_type = None
                                flatten_param = None
                                origin = get_origin(annotation)
                                param_is_list = origin is list or origin is List
                                if param_is_list:
                                    param_model_type = get_args(annotation)[0]
                                else:
                                    param_model_type = annotation

                                if get_origin(param_model_type) is Union:
                                    flatten_param = param_model_type.__name__
                                elif issubclass(param_model_type, BaseModel):
                                    flatten_param = param_model_type.model_json_schema()
                                else:
                                    flatten_param = param_model_type.__name__
                                    
                                if param_is_list:
                                    flatten_param = [flatten_param]
                                flatten_params.update({param_name: flatten_param})
                                    
                            if task_has_response and task_response_type:
                                origin = get_origin(task_response_type)
                                response_is_list = origin is list or origin is List
                                response_model_type = None
                                if response_is_list:
                                    response_model_type = get_args(task_response_type)[0]
                                else:
                                    response_model_type = task_response_type
                                if issubclass(response_model_type, BaseModel):
                                    flatten_response = response_model_type.model_json_schema()
                                else:
                                    flatten_response = response_model_type.__name__
                                if response_is_list:
                                    flatten_response = [flatten_response]
                            data.update(
                                task_params=json.dumps(flatten_params),
                                task_response=json.dumps(flatten_response),
                            )
                            await self.arbiter.create_data(task_function_cls, **data)
                    except Exception as e:
                        print('Error in creating task function: ', e)
                        raise e
                        
                if service_class.auto_start:
                    for _ in range(service_class.initial_processes):
                        await self.pending_service_queue.put(
                            await self.arbiter.create_data(
                                Service,
                                name=uuid.uuid4().hex,
                                node_id=self.node.id,
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
            service = await self.arbiter.get_data(Service, service_id)
            if service and service.state == ServiceState.ACTIVE:
                target = f"{to_snake_case(service.service_meta.name)}_listener"
                print('stop service not working')
                # await self.broker.send_message(
                #     target,
                    
                #     ArbiterDataType.ARBITER_SERVICE_UNREGISTER)

    async def health_check_func(self):
        while not self.system_task.done():
            current_time = time.time()
            description = ''
            removed_services = []
            pending_or_active_services = await self.arbiter.search_data(
                Service, state=ServiceState.PENDING)
            pending_or_active_services.extend(
                await self.arbiter.search_data(Service, state=ServiceState.ACTIVE))            
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
        try:
            async for message in self.arbiter.listen(
                self.node.unique_id, 
                ARBITER_SYSTEM_TIMEOUT
            ):
                if message is None:
                    print("Timeout in system task")
                    break
                try:
                    typed_data = ArbiterTypedData.model_validate_json(message.data)
                    message_type = ArbiterDataType(int(typed_data.type))
                    data = typed_data.data
                except Exception as e:
                    print('Error in system task: ', e)

                try:
                    response = False
                    match message_type:
                        case ArbiterDataType.API_REGISTER:
                            await self._warp_in_queue.put((
                                WarpInTaskResult.API_REGISTER_SUCCESS, data))
                        case ArbiterDataType.API_UNREGISTER:
                            await self._warp_in_queue.put((
                                WarpInTaskResult.API_REGISTER_SUCCESS, data))
                        case ArbiterDataType.PING:
                            # health check의 경우 한번에 모아서 업데이트 하는 경우를 생각해봐야한다.
                            if service := await self.arbiter.get_data(Service, data):
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
                                    await self.arbiter.update_data(service)
                                    response = True
                        case ArbiterDataType.ARBITER_SERVICE_REGISTER:
                            if await self.register_service(data):
                                response = True
                        case ArbiterDataType.ARBITER_SERVICE_UNREGISTER:
                            if unregistered_service := await self.arbiter.get_data(Service, data):
                                await self.unregister_service(unregistered_service)
                                response = True
                            else:
                                print('Service is not found')
                        case ArbiterDataType.SHUTDOWN:
                            if self.node.shutdown_code == data:
                                if not self.shutdown_flag:
                                    # pending_service_queue에 None을 넣어서
                                    # cli의 종료를 유도하여 shutdown_task를 실행한다.
                                    await self.pending_service_queue.put(None)
                                    response = True
                                else:
                                    break
                except Exception as e:
                    print('Error process message: ', e)
                    print('Message: ', message_type, data)
                finally:
                    if response:
                        await self.arbiter.push_message(
                            message.id,
                            ArbiterDataType.ACK.value
                        )
            if not self.shutdown_flag:
                print("System Task is done, before shutdown")
            await self.pending_service_queue.put(None)
        except Exception as e:
            print("Error in system task: ", e)


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))