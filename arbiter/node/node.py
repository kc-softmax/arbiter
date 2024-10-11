from __future__ import annotations
import asyncio
import sys
import time
import json
import uvicorn
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
from arbiter.gateway import ArbiterGateway
from fastapi import FastAPI
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
from arbiter.configs import ArbiterNodeConfig
from arbiter.task import ArbiterAsyncTask

class ArbiterNode():
    
    def __init__(
        self,
        *,
        config: ArbiterNodeConfig = ArbiterNodeConfig(),
        gateway_config: uvicorn.Config | None = uvicorn.Config(app=FastAPI()),
        log_level: str | None = None,
        log_format: str | None = None
    ):
        self.config = config
        self.gateway_config: uvicorn.Config = gateway_config
        if self.gateway_config:
            self.gateway_server: uvicorn.Server = uvicorn.Server(self.gateway_config)
            self.gateway = self.gateway_config.app
        else:
            self.gateway_server = None
            self.gateway = None
        
        self.log_level = log_level
        self.log_format = log_format

        self.arbiter: Arbiter = None        

        self.health_check_task: asyncio.Task = None

        self._services: list[ArbiterService] = []
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        
    @property
    def name(self) -> str:
        return self.arbiter.arbiter_config.name
    
    def setup(self, arbiter: Arbiter):
        self.arbiter = arbiter
        
    def add_service(self, service: ArbiterService):
        # change to service node
        if any(s.name == service.name for s in self._services):
            raise ValueError('Service with the same name is already added')
        self._services.append(service)

    async def clear(self):
        if self.arbiter:
            await self.arbiter.disconnect()

    async def _preparation_task(self):
        """
            만들기 전에 검사하는 단계라고 생각하면 될까?
            1차 유효성 검증 후 registry 채널에 등록 요청 한다.
        """
        try:
            pass
        except Exception as e:
            pass
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        return

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
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
        return
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
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.DISAPPEARANCE.name}...ok"))
        return
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
                print(data)
        match phase:
            case WarpInPhase.PREPARATION:
                asyncio.create_task(self._preparation_task())
                timeout = self.config.preparation_timeout
            case WarpInPhase.INITIATION:
                timeout = self.config.initialization_timeout
                asyncio.create_task(self._initialize_task())
            case WarpInPhase.DISAPPEARANCE:
                timeout = self.config.disappearance_timeout
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
        try:
            yield self
        finally:
            self.health_check_task.cancel()        
            await self.clear()
    
    async def health_check_func(
        self,
        shutdown_event: asyncio.Event,
    ):
        try:
            async for raw_message in self.arbiter.broker.listen(
                'test', self.config.system_timeout
            ):
                pass
        
        except TimeoutError as e:
            # system task function is timeout
            # 아무 메세지를 받지 못해서, timeout이 발생한다.
            # * 모든 서비스가 중단되었
            print('Health Check Task is timeout.')
            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            pass
            print("Error in system task: ", e)
        finally:
            shutdown_event.set()
            if self.gateway_server:
                self.gateway_server.should_exit = True


# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))