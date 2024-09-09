from __future__ import annotations
import os
import asyncio
import uuid
import sys
import time
import json
import importlib
from collections import defaultdict
from configparser import ConfigParser
from asyncio.subprocess import Process
from inspect import Parameter
from pydantic import BaseModel
from contextlib import asynccontextmanager
from warnings import warn
from types import UnionType
from typing_extensions import Annotated
from typing import (
    AsyncGenerator,
    Type,
    TypeVar, 
    Generic,
    Union, 
    get_origin,
    get_args,
    List
)
from arbiter import Arbiter
from arbiter.data.models import (
    ArbiterModel,
    ArbiterNode,
    ArbiterServiceModel,
    ArbiterServiceNode,
    ArbiterTaskModel,
    ArbiterTaskNode,
    ArbiterServerModel,
    ArbiterServerNode,
)
from arbiter.service import ArbiterService
from arbiter.constants import (
    WARP_IN_TIMEOUT,
    ARBITER_SERVICE_PENDING_TIMEOUT,
    ARBITER_SERVICE_ACTIVE_TIMEOUT,
    ARBITER_SYSTEM_TIMEOUT,
    ARBITER_APP_HELATH_MANAGE_FUNC_CLOCK,
)
from arbiter.enums import (
    WarpInTaskResult,
    ArbiterDataType,
    WarpInPhase,
    NodeState,
)
from arbiter.exceptions import (
    ArbiterServerNodeFaileToStartError,
    ArbiterTaskAlreadyExistsError,
    ArbiterAlreadyRegistedServiceMetaError,
    ArbiterServiceNodeFaileToStartError,
    ArbiterInconsistentServiceModelError
)
from arbiter.utils import (
    restore_type,
    get_ip_address,
    fetch_data_within_timeout,
    get_data_within_timeout,
    get_pickled_data,
    get_task_queue_name,
    terminate_process,
    transform_type_from_annotation,
    # find_python_files_in_path,
    # get_all_subclasses
)

T = TypeVar('T')


class TypedQueue(asyncio.Queue, Generic[T]):
    async def get(self) -> T:
        return await super().get()

class ArbiterApp:
    
    def __init__(
        self,
    ):
        self.config: ConfigParser = None
        self.arbiter: Arbiter = None
        self.arbiter_node: ArbiterNode = None
        self.arbiter_model: ArbiterModel = None

        self.service_manage_task: asyncio.Task = None
        self.health_manage_task: asyncio.Task = None
        self.health_check_task: asyncio.Task = None
        self.pending_service_queue: TypedQueue[ArbiterServiceNode] = TypedQueue()
        self.processes: dict[str, Process] = {}
        # 동기화 한다.
        self._services: list[Type[ArbiterService]] = []
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()

    @property
    def name(self) -> str:
        return self.config.get("project", "name", fallback="Danimoth")

    def setup(self, config: ConfigParser):
        self.config = config
        self.arbiter = Arbiter(
            host=config.get("broker", "host"),
            port=config.getint("broker", "port"),
            password=config.get("broker", "password"),
        )

    def add_service(self, service: ArbiterService):
        # check if worker.__name__ is already added
        if any(service == s for s in self._services):
            warn(f'Service {service.__name__} is already added')
        
        if any(s.__name__ == service.__name__ for s in self._services):
            raise ValueError('Service with the same name is already added')
                
        self._services.append(service)

    async def clear(self):
        if self.processes:
            for _, process in self.processes.items():
                await terminate_process(process)
        if self.health_manage_task:
            self.health_manage_task.cancel()
        if self.service_manage_task:
            self.service_manage_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.arbiter_node:
            """
                나중에 data clean 절차가 필요하다.
            """
            self.arbiter_node.state = NodeState.INACTIVE
            await self.arbiter.save_data(self.arbiter_node)

        if self.arbiter:
            await self.arbiter.disconnect()

    async def _preparation_task(self):
        """
            Arbiter Service model, Task model을 생성한다.
        """
        try:
            # deprecated
            """
            arbiter_service_in_root = find_python_files_in_path(
                from_replica=self.is_replica)
            # 프로젝트 root아래 있는 service.py 파일들을 import한다.
            for python_file in arbiter_service_in_root:
                importlib.import_module(python_file)
                # import 되었으므로 AbstractService의 subclasses로 접근 가능
            detected_workers = get_all_subclasses(ArbiterServiceWorker)
            for detected_worker in detected_workers:
                self.add_worker(detected_worker)
            """ 
            for service_node in self._services:
                assert issubclass(service_node, ArbiterService), f"{service_node} is not a subclass of ArbiterService"

                """
                    service model은 
                    arbiter model에도 등록하고
                        전체 model 파악을 위해
                    arbiter node에도 등록한다.
                        실행을 위해
                """
                created, service_model = await self._get_or_create_service_model(service_node)
                if created:
                    # 전체에서 하나만 만들어지는 model에서는
                    # 새로만든 경우에만 등록해야하므로 여기서 처리한다.
                    self.arbiter_model.service_models.append(service_model)
                    await self.arbiter.save_data(self.arbiter_model)
                await self.arbiter.save_data(service_model)
   
            await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
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
        if self.arbiter_node.is_master:
            try:
                # setup Server Model
                server_model = await self._get_or_update_server_model()

                arbiter_server_node = ArbiterServerNode(
                    arbiter_server_model_id=server_model.id,
                    arbiter_node_id=self.arbiter_node.id,
                    state=NodeState.PENDING,
                )
                
                await self.arbiter.save_data(arbiter_server_node)
                # launch Sever Node
                await self._generate_server_node(arbiter_server_node)
                
                # TODO 효율적으로 바꿔야 한다.
                fetch_data = lambda: self.arbiter.search_data(
                    ArbiterServerNode,
                    id=arbiter_server_node.id,
                    state=NodeState.ACTIVE
                )
                results = await fetch_data_within_timeout(
                    timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                    fetch_data=fetch_data,
                    check_condition=lambda data: len(data) > 0,
                )
                if not results:
                    raise ArbiterServerNodeFaileToStartError()
                # start manger fasthtml process
                await self._warp_in_queue.put(
                    (WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok")
                )
            except Exception as e:
                await self.arbiter.delete_data(arbiter_server_node)
                await self._warp_in_queue.put(
                    (WarpInTaskResult.FAIL, f"Failed to start Web Service: {e}")
                )
        else:
            await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
            
    async def _materialization_task(self):
        """
            WarpInPhase Arbiter MATERIALIZATION
            Start all services that are set to auto_start, and wait for the response
            
        """
        initial_service_models = [
            service_model
            for service_model in self.arbiter_model.service_models
            if service_model.auto_start
        ]
        try:
            for service_model in initial_service_models:
                for _ in range(service_model.num_of_services):
                    try:    
                        module = importlib.import_module(service_model.module_name)
                        getattr(module, service_model.name)
                    except (ImportError, AttributeError):
                        continue
                    pending_service = await self._start_service(service_model)
                    fetch_data = lambda: self.arbiter.search_data(
                        ArbiterServiceNode,
                        state=NodeState.ACTIVE,
                        id=pending_service.id)
                    results = await fetch_data_within_timeout(
                        timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
                        fetch_data=fetch_data,
                        check_condition=lambda data: len(data) > 0,
                    )
                    if not results:
                        raise ArbiterServiceNodeFaileToStartError

            await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.MATERIALIZATION.name}...ok"))
        except TimeoutError:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, "Failed to start initial services")
            )
        except ArbiterServiceNodeFaileToStartError:
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
        # send shutdown message to service belong to this node
        await self.arbiter.broadcast(
            topic=self.arbiter_node.get_system_channel(),
            message=self.arbiter_node.shutdown_code)
        
        fetch_data = lambda: self.arbiter.search_data(
            ArbiterServerNode,
            arbiter_node_id=self.arbiter_node.id,
            state=NodeState.ACTIVE
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
            
        fetch_data = lambda: self.arbiter.search_data(
            ArbiterServiceNode,
            arbiter_node_id=self.arbiter_node.id,
            state=NodeState.ACTIVE
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
    ) -> AsyncGenerator[ArbiterApp, Exception]:
        """
            Connect to Arbiter
            Create Master Node or Replica Node
        """
        await self.arbiter.connect()
        # Check if there is a master node with the same name (and some configuration)  
        is_master = True      
        if arbiter_models := await self.arbiter.search_data(
            ArbiterModel,
            name=self.name,
        ):
            if len(arbiter_models) > 1:
                raise ValueError('Too many Arbiter Models')           
            self.arbiter_model = arbiter_models[0]  
            active_nodes = await self.arbiter.search_data(
                ArbiterNode,
                arbiter_model_id=self.arbiter_model.id,
                state=NodeState.ACTIVE)
            if active_nodes:
                # 만약 matser node가 없으면 Master Node가 된다.
                for node in active_nodes:
                    if node.is_master:
                        is_master = False
                        break
        else:
            self.arbiter_model = ArbiterModel(
                name=self.name,
            )
        self.arbiter_node = ArbiterNode(
            state=NodeState.ACTIVE,
            arbiter_model_id=self.arbiter_model.id,
            is_master=is_master,
        )
        await self.arbiter.save_data(self.arbiter_node)
        await self.arbiter.save_data(self.arbiter_model)

        """ 
            Finish the static preparation
            and prepare for the dynamic preparation
            we called it "WarpIn"
        """
        self.health_check_task = asyncio.create_task(self.health_check_func(system_queue))
        self.service_manage_task = asyncio.create_task(self.service_manage_func())
        self.health_manage_task = asyncio.create_task(self.health_manage_func())
        
        yield self

        await self.clear()

    async def _start_process(self, command: str, process_name: str) -> Process:
        if process_name in self.processes:
            raise ValueError(f'Process {process_name} is already started.')

        process = await asyncio.create_subprocess_shell(
            command,
            # stdout=asyncio.subprocess.PIPE,
            # stderr=asyncio.subprocess.PIPE,
            shell=True
        )
        return process
    
    async def _stop_service(self, service_id: int):
        # 해당 서비스 id를 가진 서비스를 찾아서 종료한다.
        pass
        # if service := await self.arbiter.get_data(Service, service_id):
        #     if service.state != ServiceState.ACTIVE:
        #         return
        #     #node 에게
        #     await self.arbiter.update_data(service, state=ServiceState.STOPPED)
        #     fetch_data = lambda: self.arbiter.get_data(
        #         Service,
        #         service_id
        #     )
        #     try:
        #         result = await get_data_within_timeout(
        #             timeout=ARBITER_SERVICE_PENDING_TIMEOUT,
        #             fetch_data=fetch_data,
        #             check_condition=lambda data: data.state == ServiceState.INACTIVE,
        #         )
        #         if not result:
        #             # failed to stop service
        #             raise Exception('Failed to stop service')
        #     except Exception as e:
        #         # add faield log in the future
        #         pass
 
    async def _start_service(self, service_model: ArbiterServiceModel) -> ArbiterServiceNode:
        service_node = ArbiterServiceNode(
            state=NodeState.PENDING,
            arbiter_node_id=self.arbiter_node.id,
            arbiter_service_model_id=service_model.id,
        )
        await self.pending_service_queue.put(service_node)
        return service_node

    async def _generate_server_node(self, server_node: ArbiterServerNode):
        # uvicorn_worker_node = ArbiterServerNode(        
        broker_config = dict(self.config['broker'])
        server_config = dict(self.config['server'])

        params = ', '.join([
            f"'{server_node.id}'",
            f"'{broker_config.get('host')}'",
            f"{broker_config.get('port')}",
            f"'{broker_config.get('password')}'",
            f"'{server_config.get('host')}'",
            f"{server_config.get('port')}",
            f"'{server_config.get('log_level')}'",
            f"'{server_config.get('allow_origins')}'",
            f"'{server_config.get('allow_methods')}'",
            f"'{server_config.get('allow_headers')}'",
            f"'{server_config.get('allow_credentials')}'",                    
        ])
        
        uvicorn_worker_script = '\n'.join([
            "from arbiter.server import ArbiterServerService;",
            "import asyncio;",
            f"wokrer = ArbiterServerService({params});",
            f"asyncio.run(wokrer.run());"
        ])
        
        uvicorn_command = ' '.join([
            f"{sys.executable}", '-c', f'"{uvicorn_worker_script}"'
        ])
        
        process = await self._start_process(uvicorn_command, 'uvicorn')
        self.processes['uvicorn'] = process

    async def _get_or_update_server_model(
        self,
    ) -> ArbiterServerModel:
        # 현재 aribter model에 등록된 service model의 task model과 비교한다.
        if server_models := await self.arbiter.search_data(ArbiterServerModel, arbiter_model_id=self.arbiter_model.id):
            assert len(server_models) == 1, 'Too many Server Models'
            server_model = server_models[0]
        else:
            server_model = ArbiterServerModel(
                name=self.arbiter_model.name,
                arbiter_model_id=self.arbiter_model.id,
                num_of_services=1,
            )
            await self.arbiter.save_data(server_model)

        registed_http_task_models = server_model.http_task_models
        registed_stream_task_models = server_model.stream_task_models  
                  
        for service_model in self.arbiter_model.service_models:
            # service_model의 등록된 http_task_models, stream_task_models를 가져온다.
            # server model의 http_task_model 및 stream_task_model을 비교하여 없다면 추가한다.
            for task_model in service_model.task_models:
                # task_model.connection 혹은 task_model.method가 있어야 한다.
                if not task_model.connection and not task_model.method:
                    continue
                
                if not any(task_model == http_task_model for http_task_model in registed_http_task_models):
                    registed_http_task_models.append(task_model)                    
                if not any(task_model == stream_task_model for stream_task_model in registed_stream_task_models):
                    registed_stream_task_models.append(task_model)
                    
        await self.arbiter.save_data(server_model)
        return server_model
    
    async def _get_or_create_service_model(
        self,
        service: Type[ArbiterService]
    ) -> tuple[bool, ArbiterServiceModel]:
        """
            Service Worker를 생성한다.
        """
        service_name = service.__name__
        module_name = service.__module__
        # task function을 먼저 검사한다.
        assert len(service.task_functions) > 0, f"{service_name} has no task functions"
        
        task_models: list[ArbiterTaskModel] = []
        
        for task_function in service.task_functions:
            task_type = getattr(task_function, 'task_type', None)
            task_function_name = task_function.__name__
                         
            queue = getattr(task_function, 'queue', None)
            if not queue:
                # task를 생성할때 queue를 지정하지 않으면 task function의 이름을 사용한다.
                queue = get_task_queue_name(service_name, task_function.__name__)
                        
            parameters = getattr(task_function, 'parameters', {})
            return_type = getattr(task_function, 'return_type', None)
            
            transformed_parameters: dict[str, list] = defaultdict(list)
            transformed_return_type: list = []
            
            for name, parameter in parameters.items():
                assert isinstance(parameter, Parameter), f"{name} is not a parameter"
                annotation = parameter.annotation
                parameter_types = transform_type_from_annotation(annotation)
                for parameter_type in parameter_types:
                    if issubclass(parameter_type, BaseModel):
                        transformed_parameters[name].append(parameter_type.model_json_schema())
                    else:
                        transformed_parameters[name].append(parameter_type.__name__)
            if return_type:
                for return_type in transform_type_from_annotation(return_type):
                    if issubclass(return_type, BaseModel):
                        transformed_return_type.append(return_type.model_json_schema())
                    else:
                        transformed_return_type.append(return_type.__name__)
                        
            task_data = dict(
                name=task_function_name,
                service_name=service_name,
                queue=queue,
                num_of_tasks=getattr(task_function, 'num_of_tasks', 1),
                transformed_parameters=json.dumps(dict(transformed_parameters)),
                transformed_return_type=json.dumps(transformed_return_type),
            )
            
            match task_type:
                case "ArbiterTask":
                    pass
                case "ArbiterAsyncTask":
                    task_data.update(
                        stream=True)                    
                case "ArbiterHttpTask":
                    task_data.update(method=getattr(task_function, 'method', 0))
                case "ArbiterStreamTask":
                    task_data.update(
                        connection=getattr(task_function, 'connection', 0),
                        communication_type=getattr(task_function, 'communication_type', 0),
                        num_of_channels=getattr(task_function, 'num_of_channels', 1))
                case "ArbiterPeriodicTask":
                    task_data.update(interval=getattr(task_function, 'interval', 0))
                case "ArbiterSubscribeTask":
                    task_data.update(channel=getattr(task_function, 'channel', ''))
                case _:
                    raise ValueError(f'Invalid Task Type - {task_type}')
            task_model = ArbiterTaskModel(**task_data)

            if task:= await self.arbiter.get_data(ArbiterTaskModel, queue):
                if task != task_model:
                    raise Exception("Task already exists")
                    
            

            task_models.append(task_model)        
            await self.arbiter.save_data(task_model)
        # 현재 arbiter model에 등록된 service model과 비교한다.
        get_service_models = lambda _name: [
            sm
            for sm in self.arbiter_model.service_models
            if sm.name == _name]
        
        if already_service_models := get_service_models(service_name):
            # TODO if 기존 서비스 모델과 더 정교하게 비교하여 다른 경우에는 에러를 발생시킨다.
            # TODO task function이 다르면 에러를 발생시킨다.
            # raise ArbiterInconsistentServiceMetaError()
            service_model = already_service_models[0]
            for task_model in task_models:
                if same_model := next(
                    (tm for tm in service_model.task_models if tm == task_model), None):
                    pass
                    # 같은 큐를 가진 task model이 있다.
                    # 같은 parameter와 같은 return type을 가진지 검사해야 한다.
                    if same_model.transformed_parameters != task_model.transformed_parameters:
                        raise ArbiterTaskAlreadyExistsError()
                    if same_model.transformed_return_type != task_model.transformed_return_type:
                        raise ArbiterTaskAlreadyExistsError()
                # 같은 이름을 가진 큐가 없다. -> 추가한다.
                service_model.task_models.append(task_model)
            return False, service_model
        else:
            service_model = ArbiterServiceModel(
                name=service_name,
                module_name=module_name,
                auto_start=service.auto_start,
                num_of_services=service.num_of_services,
                task_models=task_models,
            )
            return True, service_model
     
    async def service_manage_func(self):
        """
            등록된 service를 
        """
        while not self.health_check_task.done():
            try:
                service_node = await self.pending_service_queue.get()
                if service_node is None:
                    # shutdown
                    break
                service_model = await self.arbiter.get_data(
                    ArbiterServiceModel, 
                    service_node.arbiter_service_model_id)
                broker_host = self.config.get("broker", "host")
                broker_port = self.config.get("broker", "port")
                broker_password = self.config.get("broker", "password")
                await self.arbiter.save_data(service_node)                
                # carefully check '' type of param annotation is str or not
                params = ', '.join([
                    f"'{service_node.id}'",
                    f"'{broker_host}'",
                    f"{broker_port}",
                    f"'{broker_password}'",
                ])
                service_start_script = '\n'.join([
                    "import asyncio;",
                    f"from {service_model.module_name} import {service_model.name};"
                    f"service_worker = {service_model.name}({params});",
                    f"asyncio.run(service_worker.run());"
                ])
                process = await self._start_process(
                    f'{sys.executable} -c "{service_start_script}"',
                    service_node.id)
                self.processes[service_model.get_service_name()] = process
            except Exception as e:
                await self.arbiter.delete_data(service_node)
                print(e, ': manager')
                break

    async def health_manage_func(self):
        """
            아직 어떤 기능을 수행할지 정하지 못하였다.
        """
        while not self.health_check_task.done():
            current_time = time.time()
            description = ''
            removed_services = []
            # pending_or_active_services = await self.arbiter.search_data(
            #     ArbiterServiceNode, state=NodeState.PENDING)
            # pending_or_active_services.extend(
            #     await self.arbiter.search_data(ArbiterServiceNode, state=NodeState.ACTIVE))            
            # for service in pending_or_active_services:
            #     elapsed_time = current_time - service.updated_at.timestamp()
            #     if service.state == NodeState.ACTIVE:
            #         description = 'Service is not responding.'
            #         timeout = ARBITER_SERVICE_ACTIVE_TIMEOUT
            #     elif service.state == NodeState.PENDING:
            #         description = f'Service is not started within {elapsed_time} seconds.'
            #         timeout = ARBITER_SERVICE_PENDING_TIMEOUT
            #     else:
            #         raise ValueError('Invalid Service State')
            #     if elapsed_time > timeout:
            #         removed_services.append((service, description))

            await asyncio.sleep(ARBITER_APP_HELATH_MANAGE_FUNC_CLOCK)

    async def health_check_func(
        self,
        system_queue: asyncio.Queue[Annotated[str, "command"]]
    ):
        try:
            async for raw_message in self.arbiter.listen(
                self.arbiter_node.get_health_check_channel(),
                ARBITER_SYSTEM_TIMEOUT
            ):
                message = get_pickled_data(raw_message)
                message_id, service_node_id = message
                # health check의 경우 한번에 모아서 업데이트 하는 경우를 생각해봐야한다.
                service_node = await self.arbiter.get_data(ArbiterServiceNode, service_node_id)
                if not service_node:
                    service_node = await self.arbiter.get_data(ArbiterServerNode, service_node_id)
                if not service_node:
                    warn(f"{service_node_id}Service is not found.")
                    continue
                if service_node.state == NodeState.PENDING:
                    warn('Service is not registered yet.')
                elif service_node.state == NodeState.INACTIVE:
                    warn(
                        """
                        Service is inactive, but service try
                        to send ping message.
                        please check the service and
                        service shutdown process.
                        """)
                else:
                    await self.arbiter.save_data(service_node)
                    await self.arbiter.push_message(message_id, ArbiterDataType.ACK)
                    
        except TimeoutError as e:
            # system task function is timeout
            # 아무 메세지를 받지 못해서, timeout이 발생한다.
            # * 모든 서비스가 중단되었
            pass
        except Exception as e:
            print("Error in system task: ", e)
        finally:
            # is it necessary?
            system_queue and await system_queue.put(None)


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))