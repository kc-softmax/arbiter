from __future__ import annotations
import asyncio
import sys
import time
import json
import importlib
from collections import defaultdict
from inspect import Parameter
from pydantic import BaseModel
from contextlib import asynccontextmanager
from warnings import warn
from typing_extensions import Annotated
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    TypeVar, 
    Generic,
)
from arbiter import Arbiter
from arbiter.service import ArbiterService
from arbiter.gateway import ArbiterGatewayService
from arbiter.data.models import (
    ArbiterNode,
    ArbiterServiceNode,
    ArbiterGatewayNode,
    ArbiterTaskNode,
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
    ArbiterServiceNodeFaileToStartError,
    ArbiterInconsistentServiceModelError
)
from arbiter.utils import (
    fetch_data_within_timeout,
    get_pickled_data,
    get_task_queue_name,
    transform_type_from_annotation,
)
from arbiter.configs import ArbiterNodeCondig, ArbiterConfig
from arbiter.task import ArbiterAsyncTask

class ArbiterNode():
    
    def __init__(
        self,
        config: ArbiterNodeCondig,
        gateway: list[ArbiterGatewayService],
        *,
        log_level: str | None = None,
        log_format: str | None = None        
    ):
        self.config = config
        self.log_level = log_level
        self.log_format = log_format

        self.arbiter: Arbiter = None        
        self.arbiter_node: ArbiterNode = None
        self.health_check_task: asyncio.Task = None

        self._gateway_nodes: list[ArbiterGatewayNode] = []
        self._service_nodes: list[ArbiterServiceNode] = []
        self._default_tasks: list[ArbiterAsyncTask] = []
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        self
        
    def handle_task(self, task: ArbiterAsyncTask):
        self._default_tasks.append(task)
        
    def setup(self, arbiter: Arbiter):
        self.arbiter = arbiter
        self.arbiter_node = ArbiterNode(
            state=NodeState.ACTIVE,
        )

        
    def add_service(self, service: ArbiterService):
        assert not isinstance(service, ArbiterGatewayService), 'gateway service is not allowed, use add_gateway method'
        # change to service node
        if any(s.name == service.name for s in self._services):
            raise ValueError('Service with the same name is already added')
        self._services.append(service)
    
    def set_gateway(self, gateway: list[ArbiterGatewayService]):
        # change gateway service to node
        self._gateway_nodes = [
            ArbiterGatewayNode(
                arbiter_node_id=self.arbiter_node.id,
                name=_gateway.name,
                options=_gateway.options,
                host=_gateway.host,
                    
                
            )
            for _gateway in gateway
        ]
        # pass
    
    async def clear(self):
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.arbiter_node:
            pass
        if self.arbiter:
            await self.arbiter.disconnect()

    async def _preparation_task(self):
        """
            만들기 전에 검사하는 단계라고 생각하면 될까?
            1차 유효성 검증 후 registry 채널에 등록 요청 한다.
        """
        try:
            if self._gateway:
                # gateway의 유효성을 체크한다.
                # routing 문제 때문에, 동일 이름이 있는지만 체크한다.
                # NODE_CHANNEL에 물어본다.
                # 여기서는 무조건 통과
                pass
            for service_info in self._services:
                """
                    service model과 task model을 생성한다.
                    만약 이름이 같다면, 가지고 있는 task model을 비교하여 다르다면 에러를 발생시킨다.
                """
                pass
                # service_model = await self._get_or_create_service_model(service_info)
                # service_info.set_service_model(service_model)
            await self._warp_in_queue.put(
                (WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        except Exception as e:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, f"Failed to prepare services: {e}"))
     
    async def _initialize_task(self):
        """
            WarpInPhase Arbiter initialization
        """
        try:
            for gateway_info in self._gateway_services:
                gateway_model = gateway_info.get_service_model()
                arbiter_gateway_node = ArbiterGatewayNode(
                    parent_model_id=gateway_model.id,                
                    arbiter_node_id=self.arbiter_node.id,
                    state=NodeState.PENDING,
                    host=gateway_info.host,
                    port=gateway_info.port,
                    log_level=gateway_info.log_level,
                    allow_origins=gateway_info.allow_origins,
                    allow_methods=gateway_info.allow_methods,
                    allow_headers=gateway_info.allow_headers,
                    allow_credentials=gateway_info.allow_credentials
                )
                await self.arbiter.save_data(arbiter_gateway_node)
                # launch Sever Node
                await self._generate_server_node(arbiter_gateway_node)

                # TODO 효율적으로 바꿔야 한다.
                fetch_data = lambda: self.arbiter.search_data(
                    ArbiterGatewayNode,
                    id=arbiter_gateway_node.id,
                    state=NodeState.ACTIVE
                )
                results = await fetch_data_within_timeout(
                    timeout=self.arbiter.config.get('service_pending_timeout'),
                    fetch_data=fetch_data,
                    check_condition=lambda data: len(data) > 0,
                )
                if not results:
                    raise ArbiterServerNodeFaileToStartError()
                message = f"'{gateway_info.name}' Gateway running on http://{gateway_info.host}:{gateway_info.port}"
                await self._warp_in_queue.put(
                    (WarpInTaskResult.INFO, message)
                )
                # TODO start manger fasthtml process
            for service_info in self._services:
                service_model = service_info.get_service_model()
                if not service_model.auto_start:
                    continue
                for _ in range(service_model.num_of_services):
                    module = importlib.import_module(service_model.module_name)
                    getattr(module, service_model.name)
                    pending_service = await self._start_service(service_model)
                    fetch_data = lambda: self.arbiter.search_data(
                        ArbiterServiceNode,
                        state=NodeState.ACTIVE,
                        id=pending_service.id)
                    results = await fetch_data_within_timeout(
                        timeout=self.arbiter.config.get('service_pending_timeout'),
                        fetch_data=fetch_data,
                        check_condition=lambda data: len(data) > 0,
                    )
                    if not results:
                        raise ArbiterServiceNodeFaileToStartError
        except (ImportError, AttributeError) as e:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, f"Failed to start initial services {e}")
            )
        except TimeoutError:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, "Failed to start initial services")
            )
        except ArbiterServiceNodeFaileToStartError:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL, "Failed to start initial services")
            )

        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
           
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
        await self.arbiter.raw_broadcast(
            topic=self.arbiter_node.get_system_channel(),
            message=self.arbiter_node.shutdown_code)
        
        fetch_data = lambda: self.arbiter.search_data(
            ArbiterGatewayNode,
            arbiter_node_id=self.arbiter_node.id,
            state=NodeState.ACTIVE
        )
        
        results = await fetch_data_within_timeout(
            timeout=self.arbiter.config.get('service_pending_timeout'),
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
            timeout=self.arbiter.config.get('service_pending_timeout'),
            fetch_data=fetch_data,
            check_condition=lambda data: len(data) == 0,
        )
        
        # if results:
            # await self._warp_in_queue.put(
            #     (WarpInTaskResult.WARNING, f"{len(results)} services are not shutdown")
            # )
                
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
                asyncio.create_task(self._preparation_task())
                timeout = self.preparation_timeout
            case WarpInPhase.INITIATION:
                timeout = self.initialization_timeout
                asyncio.create_task(self._initialize_task())
            case WarpInPhase.DISAPPEARANCE:
                timeout = self.disappearance_timeout
                asyncio.create_task(self._disappearance_task())
            case _:
                raise ValueError('Invalid WarpInPhase')
        while True:
            try:
                message = await asyncio.wait_for(
                    self._warp_in_queue.get(),
                    timeout
                )
                if message is None:
                    break
                yield message
            except asyncio.TimeoutError:
                yield (WarpInTaskResult.FAIL, f"Warp In Timeout in {phase.name} phase.")
    
    @asynccontextmanager
    async def warp_in(
        self,
        shutdown_event: asyncio.Event,
    ) -> AsyncGenerator[ArbiterNode, Exception]:
        """
            Connect to Arbiter
            Create Master Node or Replica Node
        """
        await self.arbiter.connect()
        """ 
            Finish the static preparation
            and prepare for the dynamic preparation
            we called it "WarpIn"
        """
        self.health_check_task = asyncio.create_task(self.health_check_func(shutdown_event))
        
        yield self

        await self.clear()

    async def _start_process(self, command: str):
        await asyncio.create_subprocess_shell(
            command,
            # stdout=asyncio.subprocess.PIPE,
            # stderr=asyncio.subprocess.PIPE,
            shell=True
        )
    
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
        pass
        #     try:
        #         service_node = await self.pending_service_queue.get()
        #         if service_node is None:
        #             # shutdown
        #             break
        #         service_model = await self.arbiter.get_data(
        #             ArbiterServiceModel, 
        #             service_node.parent_model_id)
        #         params = {
        #             'arbiter_name': self.arbiter_model.name,
        #             'service_node_id': service_node.id,
        #             'arbiter_host': self.arbiter.host,
        #             'arbiter_port': self.arbiter.port,
        #             'arbiter_config': self.arbiter.config,
        #         }

        #         service_start_script = '\n'.join([
        #             "import asyncio;",
        #             f"from {service_model.module_name} import {service_model.name};"
        #             f"service_worker = {service_model.name}(**{params});",
        #             f"asyncio.run(service_worker.run());"
        #         ])
        #         await self._start_process(
        #             f'{sys.executable} -c "{service_start_script}"')
        #     except Exception as e:
        #         await self.arbiter.delete_data(service_node)
        #         print(e, ': manager')
        #         break

        # service_node = ArbiterServiceNode(
        #     state=NodeState.PENDING,
        #     arbiter_node_id=self.arbiter_node.id,
        #     parent_model_id=service_model.id,
        # )
        # await self.arbiter.save_data(service_node)
        # await self.pending_service_queue.put(service_node)
        # return service_node

    async def _generate_server_node(self, gateway_node: ArbiterGatewayNode):

        params = {
            'arbiter_name': self.arbiter_model.name,
            'service_node_id': gateway_node.id,
            'arbiter_host': self.arbiter.host,
            'arbiter_port': self.arbiter.port,
            'arbiter_config': self.arbiter.config,
            'host': gateway_node.host,
            'port': gateway_node.port,
            'log_level': gateway_node.log_level,
            'allow_origins': gateway_node.allow_origins,
            'allow_methods': gateway_node.allow_methods,
            'allow_headers': gateway_node.allow_headers,
            'allow_credentials': gateway_node.allow_credentials,
        }

        gateway_script = '\n'.join([
            "from arbiter.gateway import ArbiterGatewayService;",
            "import asyncio;",
            f"worker = ArbiterGatewayService(**{params});",
            "asyncio.run(worker.run());"
        ])
        
        gateway_command = ' '.join([
            f"{sys.executable}", '-c', f'"{gateway_script}"'
        ])
        
        await self._start_process(gateway_command)
    
    async def _get_or_create_service_model(
        self,
        service_info: ArbiterServiceInfo
    ) -> ArbiterServiceModel:
        """
            Service Worker를 생성한다.
        """
        service = service_info.klass
        service_name = service_info.name
        gateway_name = service_info.gateway
        
        if gateway_models := await self.arbiter.search_data(
            ArbiterGatewayModel,
            arbiter_node_model_id=self.arbiter_model.id,
            name=gateway_name
        ):
            if len(gateway_models) > 1:
                raise ValueError('Too many Gateway Models')
            gateway_model_id = gateway_models[0].id
        else:
            gateway_model_id = ''
            
        module_name = service.__module__
        # task function을 먼저 검사한다.
        assert len(service.task_functions) > 0, f"{service_name} has no task functions"

        new_service_model = ArbiterServiceModel(
            arbiter_node_model_id=self.arbiter_model.id,
            gateway_model_id=gateway_model_id,
            name=service_name,
            module_name=module_name,
            auto_start=service.auto_start,
            num_of_services=service.num_of_services)

        task_models: list[ArbiterTaskModel] = []
        
        for task_function in service.task_functions:
            task_function_name = task_function.__name__
                         
            queue = getattr(task_function, 'queue', None)
            
            # task를 생성할때 queue를 지정하지 않으면 task function의 이름을 사용한다.
            if not queue:
                queue = get_task_queue_name(service_name, task_function.__name__)
                
            for task_model in task_models:
                if task_model.queue == queue:
                    raise ArbiterTaskAlreadyExistsError()
                 
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
                service_model_id=new_service_model.id,
                name=task_function_name,
                service_name=service_name,
                queue=queue,
                num_of_tasks=getattr(task_function, 'num_of_tasks', 1),
                stream=getattr(task_function, 'stream', False),
                http=getattr(task_function, 'http', False),
                request=getattr(task_function, 'request', False),
                file=getattr(task_function, 'file', False),
                transformed_parameters=json.dumps(dict(transformed_parameters)),
                transformed_return_type=json.dumps(transformed_return_type),
            )

            task_model = ArbiterTaskModel(**task_data)

            task_models.append(task_model)
        
        for service_model in await self.arbiter.search_data(
            ArbiterServiceModel,
            arbiter_node_model_id=self.arbiter_model.id
        ):
            # 같은걸 찾음
            if service_model.name == service_name:
                # 이름이 같다면 - 테스크 모델이 모두 같아야 한다. * 현재 조건
                other_task_models = await self.arbiter.search_data(
                    ArbiterTaskModel, service_model_id=service_model.id)
                if len(task_models) != len(other_task_models):
                    # 이름을 바꾸던가 해라
                    raise ArbiterInconsistentServiceModelError()
                
                for task_model in task_models:
                    if same_model := next(
                        (tm for tm in other_task_models if tm == task_model), None):
                        # 같은 큐를 가진 task model이 있다.
                        # 같은 parameter와 같은 return type을 가진지 검사해야 한다.
                        if same_model.transformed_parameters != task_model.transformed_parameters:
                            raise ArbiterInconsistentServiceModelError()
                        if same_model.transformed_return_type != task_model.transformed_return_type:
                            raise ArbiterInconsistentServiceModelError()
                    else:
                        # 같은 큐를 가진 task model이 없다. 현재는 에러를 발생시킨다.
                        raise ArbiterInconsistentServiceModelError()
                return service_model
        # 새롭게 저장해야 한다.
        # 먼저 task model을 비교하여 같은게 있는지 확인한다.
        new_service_model.task_model_ids = [
            task_model.get_id()
            for task_model in task_models]
        await self.arbiter.save_data(new_service_model)
        for task_model in task_models:
            if await self.arbiter.get_data(ArbiterTaskModel, queue):
                print('Task Already Exists', queue)
                raise ArbiterTaskAlreadyExistsError()
            task_model.service_model_id = new_service_model.id
            await self.arbiter.save_data(task_model)
            
        return new_service_model
    
    async def health_check_func(
        self,
        shutdown_event: asyncio.Event,
    ):
        try:
            async for raw_message in self.arbiter.broker.listen(
                self.arbiter_node.get_health_check_channel(),
                self.system_timeout
            ):
                message = get_pickled_data(raw_message)
                message_id, service_node_id = message
                # health check의 경우 한번에 모아서 업데이트 하는 경우를 생각해봐야한다.
                service_node = await self.arbiter.get_data(ArbiterServiceNode, service_node_id)
                if not service_node:
                    service_node = await self.arbiter.get_data(ArbiterGatewayNode, service_node_id)
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
            print('Health Check Task is timeout.')
            pass
        except Exception as e:
            print("Error in system task: ", e)
        finally:
            shutdown_event.set()


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))