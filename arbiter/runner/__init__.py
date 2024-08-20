from __future__ import annotations
import asyncio
import uuid
import sys
import importlib
import time
import json
from asyncio.subprocess import Process
from inspect import Parameter
from pydantic import BaseModel
from contextlib import asynccontextmanager
from warnings import warn
from types import UnionType
from typing_extensions import Annotated
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
    WebService,
    WebServiceTask,
    ArbiterTaskModel
)
from arbiter.service import AbstractService
from arbiter.constants import (
    ArbiterTypedData,
    WARP_IN_TIMEOUT,
    ARBITER_SERVICE_PENDING_TIMEOUT,
    ARBITER_SERVICE_ACTIVE_TIMEOUT,
    ARBITER_SYSTEM_TIMEOUT)
from arbiter.constants.enums import (
    WarpInTaskResult,
    ArbiterDataType,
    WarpInPhase,
    ServiceState
)
from arbiter.exceptions import (
    ArbiterTimeOutError,
    ArbiterTaskAlreadyExistsError,
    ArbiterNoWebServiceError,
    ArbiterTooManyWebServiceError,
    ArbiterAlreadyRegistedServiceMetaError,
    ArbiterInconsistentServiceMetaError
)
from arbiter.utils import (
    find_python_files_in_path,
    get_all_subclasses,
    get_ip_address,
    fetch_data_within_timeout,
    get_data_within_timeout,
    terminate_process,
    get_task_queue_name,
)

T = TypeVar('T')


class TypedQueue(asyncio.Queue, Generic[T]):
    async def get(self) -> T:
        return await super().get()

class ArbiterRunner:
    
    @property
    def is_replica(self) -> bool:
        return self.node.master_id > -1

    def __init__(
        self,
        name: str,
        config: dict[str, str] = {}
    ):
        self.name = name
        self.config = config
        self.node: Node = None
        self.wsgi_app_id: str = None
        self.service_metas: list[ServiceMeta] = []
        self.arbiter: Arbiter = Arbiter()

        self.service_task: asyncio.Task = None
        self.system_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.pending_service_queue: TypedQueue[Service] = TypedQueue()
        self.processes: dict[str, Process] = {}
        # 동기화 한다.
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown_queue: asyncio.Queue = asyncio.Queue()

    async def clear(self):
        if self.processes:
            for _, process in self.processes.items():
                await terminate_process(process)
        if self.service_task:
            self.service_task.cancel()
        if self.system_task:
            self.system_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.node:
            """
                나중에 data clean 절차가 필요하다.
            """
            await self.arbiter.update_data(
                self.node,
                state=ServiceState.INACTIVE
            )

        if self.arbiter:
            await self.arbiter.disconnect()

    async def register_service(self, service_id: str):
        if service := await self.arbiter.get_data(Service, service_id):
            await self.arbiter.update_data(
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
        await self.arbiter.update_data(
            service,
            state=ServiceState.INACTIVE,
            description=description,
        )

    async def _preparation_task(self):
        """
            Find all python files in the root directory and find all subclasses of AbstractService
                # ignore or filtering 
            Create ServiceMeta from AbstractService subclasses
            Create TaskFunction from each ServiceMeta
        """
        """
            #MARK 절대경로, 상대경로 둘 다 사용가능하게 변경해야 한다.
        """
        try:
            arbiter_service_in_root = find_python_files_in_path(
                from_replica=self.is_replica)
            # 프로젝트 root아래 있는 service.py 파일들을 import한다.
            for python_file in arbiter_service_in_root:
                importlib.import_module(python_file)
                # import 되었으므로 AbstractService의 subclasses로 접근 가능
            service_classes = get_all_subclasses(AbstractService)
            for service_class in service_classes:
                assert issubclass(service_class, AbstractService)
                service_meta_data = dict(
                    node_id=self.node.id,
                    name=service_class.__name__,
                    module_name=service_class.__module__,
                    auto_start=service_class.auto_start   
                )
                # master 와 replica는 다른 행동을 한다.
                if self.is_replica:
                    service_meta_data.update(from_master=True)
                    # 만약 존재한다면, 두 개는 서로 같아야 한다.
                    if master_service_metas := await self.arbiter.search_data(
                        ServiceMeta,
                        node_id=self.node.id,
                        name=service_class.__name__,
                    ):
                        if len(master_service_metas) > 1:
                            raise Exception(f"ServiceMeta {service_class.__name__} is already registered")
                        service_meta = master_service_metas[0]
                        if service_meta.model_dump() != service_meta_data:
                            raise ArbiterInconsistentServiceMetaError()
                        # 존재하며, 두 개가 같다. ArbiterTaskModel을 만들 필요가 없다.
                        continue
                    else:
                        # 존재하지 않으면 만든다.
                        service_meta = await self.arbiter.create_data(
                            ServiceMeta,
                            **service_meta_data
                        )
                else:
                    service_meta_data.update(from_master=True)
                    # master인 경우는 무조건 만든다.
                    # 중복되면 안된다.
                    if await self.arbiter.search_data(
                        ServiceMeta,
                        node_id=self.node.id,
                        name=service_class.__name__,
                    ):
                        raise ArbiterAlreadyRegistedServiceMetaError(f"ServiceMeta {service_class.__name__} is already registered")

                    service_meta = await self.arbiter.create_data(
                        ServiceMeta,
                        **service_meta_data
                    )
                    
                if tasks := service_class.tasks:
                    for task in tasks:
                        task_name = task.__name__                    
                        queue = getattr(task, 'queue', None)
                        if not queue:
                            # default queue name
                            queue = get_task_queue_name(
                                service_class.__name__,
                                task_name
                            )
                        # assert queue is not None, 'Task Queue is not found'
                        params = getattr(task, 'params', {})
                        assert params is not None, 'Task Params is not found'
                        task_response_type = getattr(task, 'response_type', None)
                        task_has_response = getattr(task, 'has_response', True)
                        # response type 이 있을경우 has_response는 True여야 한다.
                        assert task_response_type is None or task_has_response, 'Task has response but response type is not found'
                        
                        flatten_params = {}
                        flatten_response = ''
                        
                        for param_name, parameter in params.items():
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
                            elif get_origin(param_model_type) is UnionType:
                                args = get_args(param_model_type)
                                param_type = args[0] if args else None
                                if not param_type:
                                    flatten_param = 'Any'
                                else:
                                    flatten_param = param_type.__name__
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
                                        
                        data = dict(
                            service_meta=service_meta,
                            name=task_name,
                            queue=queue,
                            method=getattr(task, 'method', 0),
                            connection_info=getattr(task, 'connection_info', False),
                            connection=getattr(task, 'connection', 0),
                            communication_type=getattr(task, 'communication_type', 0),
                            num_of_channels=getattr(task, 'num_of_channels', 1),
                            num_of_tasks=getattr(task, 'num_of_tasks', 1),
                            params=json.dumps(flatten_params),
                            response=json.dumps(flatten_response),
                        )
                        # queue에 대한 중복검사를 해야한다.
                        if await self.arbiter.search_data(
                            ArbiterTaskModel,
                            service_meta=service_meta,
                            queue=queue
                        ):
                            raise ArbiterTaskAlreadyExistsError(f"Task Queue {queue} is already registered")
                        
                        await self.arbiter.create_data(ArbiterTaskModel, **data)
                self.service_metas.append(service_meta)
            await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        except ArbiterTaskAlreadyExistsError:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, f"Task Queue {queue} is already registered"))
        except Exception as e:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, f"Failed to prepare services: {e}"))
     
    async def _initialize_task(self):
        """
            WarpInPhase Arbiter initialization
            
            if node is Master, execute wsgi app with the number of workers
                and wait for the response from the each gunicorn woker
                
            if node is Replica, send the message to the master node
            
            
            check database is working
        """
        # wsgi, asgi 선택하자
        if not self.is_replica:
            try:
                # gunicorn 실행
                # start gunicorn
                host = self.config.get("api", "host", fallback=None)
                port = self.config.get("api", "port", fallback=None)
                worker_count = self.config.get("api", "worker_count", fallback=1)
                log_level = self.config.get("api", "log_level", fallback="info")
                gunicorn_command = ' '.join([
                    f'NODE_ID={self.node.unique_id}',
                    'gunicorn',
                    '-w', f"{worker_count}",  # Number of workers
                    '--bind', f"{host}:{port}",  # Bind to port 8080
                    '-k', 'arbiter.api.ArbiterUvicornWorker',  # Uvicorn worker class
                    '--log-level', log_level,  # Log level
                    'arbiter.api:get_app'  # Application module and variable,
                ])
                await self._start_process(gunicorn_command, 'gunicorn')
                # fastAPI 서버가 실행되면서 보내오는 메세지를 받아야 한다.
                # -> database 에서 해당 서비스를 찾아서 상태를 변경한다.
                # 예제 사용법            
                fetch_data = lambda: self.arbiter.search_data(
                    WebService,
                    node_id=self.node.unique_id
                )
                results = await fetch_data_within_timeout(
                    timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                    fetch_data=fetch_data,
                    check_condition=lambda data: len(data) >= worker_count,
                )
                if not results:
                    raise ArbiterNoWebServiceError()
                elif len(results) > worker_count:
                    raise ArbiterTooManyWebServiceError()
                elif len(results) < worker_count:
                    await self._warp_in_queue.put(
                        (WarpInTaskResult.WARNING, f"Not enough Web Services are started, {len(results)} expected {worker_count}")
                    )
                # start manger fasthtml process                
                await self._warp_in_queue.put(
                    (WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok")
                )
            except ArbiterNoWebServiceError as e:
                await self._warp_in_queue.put(
                    (WarpInTaskResult.FAIL, f"Failed to start Web Service: {e}")
                )
            except ArbiterTooManyWebServiceError as e:
                await self._warp_in_queue.put(
                    (WarpInTaskResult.FAIL, f"Failed to start Web Service: {e}")
                )
            except Exception as e:
                await self._warp_in_queue.put(
                    (WarpInTaskResult.FAIL, f"Failed to start Web Service: {e}")
                )
        else:
            await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
            
    async def _channeling_task(self):
        """"
            WarpInPhase Arbiter CHANNELING
            try to regist all task function in this node
            broadcast api register channel
            how to handle the response?
            may be handle fastapi app to model 
        """
        web_services = await self.arbiter.search_data(WebService, node_id=self.node.unique_id)
        if service_metas := await self.arbiter.search_data(ServiceMeta, node_id=self.node.id):
            for service_meta in service_metas:
                regist_task_count = 0
                if task_models := await self.arbiter.search_data(
                    ArbiterTaskModel, service_meta=service_meta):
                    for task_model in task_models:
                        if task_model.method or task_model.connection:
                            # add route in arbiter
                            regist_task_count += 1
                            await self.arbiter.broadcast(
                                self.node.get_routing_channel(),
                                task_model.model_dump_json())
                # async gather 로 확인하는 방법도 있다.  
                for web_service in web_services:
                    task_fetch_data = lambda: self.arbiter.search_data(
                        WebServiceTask,
                        web_service_id=web_service.id
                    )
                    try:
                        await fetch_data_within_timeout(
                            timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                            fetch_data=task_fetch_data,
                            check_condition=lambda data: len(data) >= regist_task_count,
                        )
                    except TimeoutError:
                        await self._warp_in_queue.put(
                            (WarpInTaskResult.FAIL, f"Failed to register Task Function for {service_meta.name} in {web_service.app_id}")
                        )
                        return
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.CHANNELING.name}...ok"))
    
    async def _materialization_task(self):
        """
            WarpInPhase Arbiter MATERIALIZATION
            Start all services that are set to auto_start, and wait for the response
        """
        has_initial_service = False
        if service_metas := await self.arbiter.search_data(ServiceMeta, node_id=self.node.id):
            for service_meta in service_metas:
                if service_meta.auto_start:
                    # TODO Change gather to fetch_data_within_timeout
                    has_initial_service = True
                    await self._start_service(service_meta)
        try:
            if has_initial_service:
                service_fetch_data = lambda: self.arbiter.search_data(
                    Service,
                    state=ServiceState.PENDING,
                    node_id=self.node.id,
                )
                await fetch_data_within_timeout(
                    timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                    fetch_data=service_fetch_data,
                    check_condition=lambda data: len(data) < 1,
                )
            await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.MATERIALIZATION.name}...ok"))
        except TimeoutError:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, "Failed to start initial services")
            )
    
    async def _disappearance_task(self):
        """
            WarpInPhase Arbiter DISAPPEARANCE
            stop all web service with ternimate gunicorn process
            
            if master
                broadcast shutdown message to all nodes
            broadcast shutdown message to all services in node
            check database            
        """
        gunicorn_process = self.processes.pop('gunicorn', None)
        if gunicorn_process:
            web_services = await self.arbiter.search_data(WebService, node_id=self.node.unique_id)
            await terminate_process(gunicorn_process)
            fetch_data = lambda: self.arbiter.search_data(
                WebService,
                node_id=self.node.unique_id,
                state=ServiceState.INACTIVE
            )
            results = await fetch_data_within_timeout(
                timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                fetch_data=fetch_data,
                check_condition=lambda data: len(data) >= len(web_services),
            )
            if web_services and not results:
                await self._warp_in_queue.put(
                    (WarpInTaskResult.FAIL, "Failed to stop Web Service")
                )
            elif len(results) < len(web_services):
                await self._warp_in_queue.put(
                    (WarpInTaskResult.WARNING, f"Not enough Web Services are stopped, {len(results)} expected {len(web_services)}")
                )
        

        # send shutdown message to service belong to this node
        await self.arbiter.broadcast(
            topic=self.node.get_system_channel(),
                message=ArbiterTypedData(
                    type=ArbiterDataType.SHUTDOWN,
                    data=self.node.unique_id
                ).model_dump_json()
            )
        
        if not self.is_replica:
            fetch_replica_nodes = lambda: self.arbiter.search_data(
                Node,
                state=ServiceState.ACTIVE,
                name=self.name,
                master_id=self.node.id
            )
            if replica_nodes := await fetch_replica_nodes():
                for replica_node in replica_nodes:
                    # send shutdown message to all replica nodes                    
                    await self.arbiter.send_message(
                        receiver_id=replica_node.unique_id,
                        data=ArbiterTypedData(
                            type=ArbiterDataType.SHUTDOWN,
                            data=replica_node.shutdown_code
                        ).model_dump_json()
                    )
                results = await fetch_data_within_timeout(
                    timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                    fetch_data=fetch_replica_nodes,
                    check_condition=lambda data: len(data) == 0,
                )
                if results:
                    await self._warp_in_queue.put(
                        (WarpInTaskResult.WARNING, f"{len(results)} nodes are not shutdown")
                    )
        # check all services are shutdown
        # try catch로 감싸서 에러를 처리해야 한다.
        fetch_data = lambda: self.arbiter.search_data(
            Service,
            node_id=self.node.id,
            state=ServiceState.ACTIVE
        )

        results = await fetch_data_within_timeout(
            timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
            fetch_data=fetch_data,
            check_condition=lambda data: len(data) == 0,
        )
        if results:
            await self._warp_in_queue.put(
                (WarpInTaskResult.WARNING, f"{len(results)} services are not shutdown")
            )
                
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.DISAPPEARANCE.name}...ok"))
                
    async def start_phase(self, phase: WarpInPhase) -> AsyncGenerator[tuple[WarpInTaskResult, str], None]:
        # if warp_in_queue is empty, then start the phase
        if not self._warp_in_queue.empty():
            warn('Warp In Queue is not empty')
            # remove all messages in the queue
            while not self._warp_in_queue.empty():
                data = self._warp_in_queue.get_nowait()
                
        match phase:
            case WarpInPhase.PREPARATION:
                """
                    service_meta를 생성하면서
                    task function들을 검사한다.
                """
                asyncio.create_task(self._preparation_task())
            case WarpInPhase.INITIATION:
                """
                    node가 master인 경우 gunicorn을 실행한다.
                """
                asyncio.create_task(self._initialize_task())
            case WarpInPhase.CHANNELING:
                """
                    task function을 arbiter에 등록한다.
                """
                asyncio.create_task(self._channeling_task())
            case WarpInPhase.MATERIALIZATION:
                """
                    auto_start가 설정된 service들을 실행한다.
                """
                asyncio.create_task(self._materialization_task())
            case WarpInPhase.DISAPPEARANCE:
                """
                """
                asyncio.create_task(self._disappearance_task())
            case _:
                raise ValueError('Invalid WarpInPhase')
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
    async def warp_in(
        self,
        system_queue: asyncio.Queue[Annotated[str, "command"]]
    ) -> AsyncGenerator[ArbiterRunner, Exception]:
        """
            Connect to Arbiter
            Create Master Node or Replica Node
        """
        await self.arbiter.connect()


        # Check if there is a master node with the same name (and some configuration)        
        if previous_nodes := await self.arbiter.search_data(
            Node,
            name=self.name,
            state=ServiceState.ACTIVE
        ):
            # find master node in previous nodes
            if master_node := next((node for node in previous_nodes if node.master_id < 0), None):
                master_id = master_node.id
            else:
                raise ValueError('Master Node is not found, but there are nodes with the same name.')
        else:
            master_id = -1 # master node id is -1
        
        self.node = await self.arbiter.create_data(
            Node,
            name=self.name,
            ip_address=get_ip_address(),
            state=ServiceState.ACTIVE,
            master_id=master_id
        )
                
        """
            Finish the static preparation
            and prepare for the dynamic preparation
            we called it "WarpIn"
        """
        self.system_task = asyncio.create_task(self.system_task_func(system_queue))
        self.service_task = asyncio.create_task(self.service_manage_func())
        self.health_check_task = asyncio.create_task(self.health_check_func())
        yield self

        await self.clear()

    async def _start_process(self, command: str, process_name: str):
        if process_name in self.processes:
            raise ValueError(f'Process {process_name} is already started.')
        process = await asyncio.create_subprocess_shell(
            command,
            # stdout=asyncio.subprocess.PIPE,
            # stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        self.processes[process_name] = process
    
    async def _stop_service(self, service_id: int):
        # 해당 서비스 id를 가진 서비스를 찾아서 종료한다.
        if service := await self.arbiter.get_data(Service, service_id):
            if service.state != ServiceState.ACTIVE:
                return
            #node 에게
            await self.arbiter.update_data(service, state=ServiceState.STOPPED)
            fetch_data = lambda: self.arbiter.get_data(
                Service,
                service_id
            )
            try:
                result = await get_data_within_timeout(
                    timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                    fetch_data=fetch_data,
                    check_condition=lambda data: data.state == ServiceState.INACTIVE,
                )
                if not result:
                    # failed to stop service
                    raise Exception('Failed to stop service')
            except Exception as e:
                # add faield log in the future
                pass
 
    async def _start_service(self, service_meta: ServiceMeta):
        """
            1. Service 객체를 생성한다. (Pending)
            2. generate start command
            2. Process를 실행한다.
            
        """
        # sub process를 실행시킨다.
        service = await self.arbiter.create_data(
            Service,
            name=uuid.uuid4().hex,
            node_id=self.node.id,
            state=ServiceState.PENDING,
            service_meta=service_meta)
        await self.pending_service_queue.put(service)
 
    async def service_manage_func(self):
        """
            등록된 service를  
        """
        while not self.system_task.done():
            try:
                service = await self.pending_service_queue.get()
                if service is None:
                    # shutdown
                    break
                service_meta: ServiceMeta = service.service_meta
                start_command =f"""
import asyncio;
from {service_meta.module_name} import {service_meta.name};
asyncio.run({service_meta.name}.launch('{self.node.unique_id}', '{service.id}'));"""
                await self._start_process(
                    f'{sys.executable} -c "{start_command}"',
                    service.get_service_name())
            except Exception as e:
                print(e, ': manager')
                break


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

    async def system_task_func(
        self,
        system_queue: asyncio.Queue[Annotated[str, "command"]]
    ):
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
                    response_data = ArbiterDataType.ACK.value
                    match message_type:
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
                                elif service.state == ServiceState.STOPPED:
                                    response = True
                                    response_data = service.shutdown_code
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
                                # for graceful shutdown
                                await system_queue.put(None)
                except Exception as e:
                    print('Error process message: ', e)
                    print('Message: ', message_type, data)
                finally:
                    response and await self.arbiter.push_message(
                        message.id,
                        response_data
                    )
        except Exception as e:
            print("Error in system task: ", e)
        finally:
            # is it necessary?
            system_queue and await system_queue.put(None)


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))