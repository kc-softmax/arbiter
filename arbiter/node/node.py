from __future__ import annotations
import asyncio
import sys
import time
import json
import uvicorn
import importlib
import pickle
from multiprocessing import Queue as MPQueue
from aiomultiprocess import Process
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
from fastapi import FastAPI
from arbiter import Arbiter
# from arbiter.service import ArbiterService
from arbiter._service import ArbiterService
from arbiter.registry import Registry
from arbiter.gateway import ArbiterGateway

from arbiter.data.models import (
    ArbiterNode as ArbiterNodeModel,
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
from arbiter.configs import ArbiterNodeConfig, ArbiterConfig
from arbiter.task import ArbiterAsyncTask

class ArbiterNode():
    
    def __init__(
        self,
        *,
        arbiter_config: ArbiterConfig,
        node_config: ArbiterNodeConfig = ArbiterNodeConfig(),
        gateway: FastAPI | uvicorn.Config | None = FastAPI(),
        log_level: str | None = None,
        log_format: str | None = None
    ):
        self.arbiter_config = arbiter_config
        self.node_config = node_config
        if isinstance(gateway, FastAPI):
            self.gateway_config = uvicorn.Config(app=gateway)
            self.gateway_server = uvicorn.Server(self.gateway_config)
            self.gateway = gateway
        elif isinstance(gateway, uvicorn.Config):
            self.gateway_config = gateway
            self.gateway_server = uvicorn.Server(self.gateway_config)
            self.gateway = gateway.app
        else:
            self.gateway_config = None
            self.gateway_server = None
            self.gateway = None
        
        self.log_level = log_level
        self.log_format = log_format

        self.internal_shutdown_event = asyncio.Event()        
        self.arbiter = Arbiter(arbiter_config)
        self.registry: Registry = Registry()

        self._services: list[ArbiterService] = []
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        self._arbiter_processes: list[Process] = []
        self._internal_mp_queue: MPQueue = MPQueue()
        
    @property
    def name(self) -> str:
        return self.arbiter.arbiter_config.name
    
    def add_service(self, service: ArbiterService):
        # change to service node
        if any(s.name == service.name for s in self._services):
            raise ValueError('Service with the same name is already added')
        self._services.append(service)
    
    def clear_services(self):
        self._services.clear()

    async def clear(self):
        self.arbiter and await self.arbiter.disconnect()

    def start_gateway(self, shutdown_event: asyncio.Event) -> asyncio.Task:
        async def _gateway_loop():
            while not shutdown_event.is_set():
                self.gateway_server.should_exit = False
                await self.gateway_server.serve()
                # TODO 1초면 종료 다 할 수 있나? 다른 
                await asyncio.sleep(1)
        return asyncio.create_task(_gateway_loop())

    def stop_gateway(self):
        if self.gateway_server:
            self.gateway_server.should_exit = True

    def create_local_registry(self):
        # 자신의 registry는 local_node로 관리한다
        arbiter_node = ArbiterNodeModel(
            name=self.name,
            state=NodeState.ACTIVE
        )
        for service in self._services:
            self.registry.create_local_serivce_node(service.service_node)
            for task in service.tasks:
                self.registry.create_local_task_node(task.task_node)
        self.registry.create_local_node(arbiter_node)

    async def _preparation_task(self):
        """
            만들기 전에 검사하는 단계라고 생각하면 될까?
            1차 유효성 검증 후 registry 채널에 등록 요청 한다.
        """
        try:
            # ArbiterNode에 등록된 하위 노드의 process 객체를 생성한다
            for service_node in self._services:
                process = Process(
                    name=service_node.name,
                    target=service_node.run,
                    args=(self._internal_mp_queue,)
                )
                self._arbiter_processes.append(process)
                for task in service_node.tasks:
                    process = Process(
                        name=task.name,
                        target=task.run,
                        args=(self._internal_mp_queue,)
                    )
                    self._arbiter_processes.append(process)
        except Exception as e:
            pass
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        return

        # try:
        #     if self._gateway:
        #         # gateway의 유효성을 체크한다.
        #         # routing 문제 때문에, 동일 이름이 있는지만 체크한다.
        #         # NODE_CHANNEL에 물어본다.
        #         # 여기서는 무조건 통과
        #         pass
        #     for service_info in self._services:
        #         """
        #             service model과 task model을 생성한다.
        #             만약 이름이 같다면, 가지고 있는 task model을 비교하여 다르다면 에러를 발생시킨다.
        #         """
        #         pass
        #         # service_model = await self._get_or_create_service_model(service_info)
        #         # service_info.set_service_model(service_model)
        #     await self._warp_in_queue.put(
        #         (WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        # except Exception as e:
        #     await self._warp_in_queue.put(
        #         (WarpInTaskResult.FAIL, f"Failed to prepare services: {e}"))
     
    async def _initialize_task(self):
        """
            WarpInPhase Arbiter initialization
        """
        # process 객체를 실행시킨다
        for process in self._arbiter_processes:
            process.start()
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
        return
        # try:
        #     for gateway_info in self._gateway_services:
        #         gateway_model = gateway_info.get_service_model()
        #         arbiter_gateway_node = ArbiterGatewayNode(
        #             parent_model_id=gateway_model.id,                
        #             arbiter_node_id=self.arbiter_node.id,
        #             state=NodeState.PENDING,
        #             host=gateway_info.host,
        #             port=gateway_info.port,
        #             log_level=gateway_info.log_level,
        #             allow_origins=gateway_info.allow_origins,
        #             allow_methods=gateway_info.allow_methods,
        #             allow_headers=gateway_info.allow_headers,
        #             allow_credentials=gateway_info.allow_credentials
        #         )
        #         await self.arbiter.save_data(arbiter_gateway_node)
        #         # launch Sever Node
        #         await self._generate_server_node(arbiter_gateway_node)

        #         # TODO 효율적으로 바꿔야 한다.
        #         fetch_data = lambda: self.arbiter.search_data(
        #             ArbiterGatewayNode,
        #             id=arbiter_gateway_node.id,
        #             state=NodeState.ACTIVE
        #         )
        #         results = await fetch_data_within_timeout(
        #             timeout=self.arbiter.config.get('service_pending_timeout'),
        #             fetch_data=fetch_data,
        #             check_condition=lambda data: len(data) > 0,
        #         )
        #         if not results:
        #             raise ArbiterServerNodeFaileToStartError()
        #         message = f"'{gateway_info.name}' Gateway running on http://{gateway_info.host}:{gateway_info.port}"
        #         await self._warp_in_queue.put(
        #             (WarpInTaskResult.INFO, message)
        #         )
        #         # TODO start manger fasthtml process
        #     for service_info in self._services:
        #         service_model = service_info.get_service_model()
        #         if not service_model.auto_start:
        #             continue
        #         for _ in range(service_model.num_of_services):
        #             module = importlib.import_module(service_model.module_name)
        #             getattr(module, service_model.name)
        #             pending_service = await self._start_service(service_model)
        #             fetch_data = lambda: self.arbiter.search_data(
        #                 ArbiterServiceNode,
        #                 state=NodeState.ACTIVE,
        #                 id=pending_service.id)
        #             results = await fetch_data_within_timeout(
        #                 timeout=self.arbiter.config.get('service_pending_timeout'),
        #                 fetch_data=fetch_data,
        #                 check_condition=lambda data: len(data) > 0,
        #             )
        #             if not results:
        #                 raise ArbiterServiceNodeFaileToStartError
        # except (ImportError, AttributeError) as e:
        #     await self._warp_in_queue.put(
        #         (WarpInTaskResult.FAIL, f"Failed to start initial services {e}")
        #     )
        # except TimeoutError:
        #     await self._warp_in_queue.put(
        #         (WarpInTaskResult.FAIL, "Failed to start initial services")
        #     )
        # except ArbiterServiceNodeFaileToStartError:
        #     await self._warp_in_queue.put(
        #         (WarpInTaskResult.FAIL, "Failed to start initial services")
        #     )

        # await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
           
    async def _disappearance_task(self):
        """
            WarpInPhase Arbiter DISAPPEARANCE
            stop all web service with ternimate gunicorn process
            
            if master
                broadcast shutdown message to all nodes
            broadcast shutdown message to all services in node
            check database            
        """
        for process in self._arbiter_processes:
            if process.is_alive():
                process.close()
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.DISAPPEARANCE.name}...ok"))
        return
        # send shutdown message to service belong to this node
        # await self.arbiter.raw_broadcast(
        #     topic=self.arbiter_node.get_system_channel(),
        #     message=self.arbiter_node.shutdown_code)
        
        # fetch_data = lambda: self.arbiter.search_data(
        #     ArbiterGatewayNode,
        #     arbiter_node_id=self.arbiter_node.id,
        #     state=NodeState.ACTIVE
        # )
        
        # results = await fetch_data_within_timeout(
        #     timeout=self.arbiter.config.get('service_pending_timeout'),
        #     fetch_data=fetch_data,
        #     check_condition=lambda data: len(data) == 0,
        # )
        
        # if results:
        #     await self._warp_in_queue.put(
        #         (WarpInTaskResult.WARNING, f"{len(results)} services are not shutdown")
        #     )
            
        # fetch_data = lambda: self.arbiter.search_data(
        #     ArbiterServiceNode,
        #     arbiter_node_id=self.arbiter_node.id,
        #     state=NodeState.ACTIVE
        # )
        
        # results = await fetch_data_within_timeout(
        #     timeout=self.arbiter.config.get('service_pending_timeout'),
        #     fetch_data=fetch_data,
        #     check_condition=lambda data: len(data) == 0,
        # )
        
        # # if results:
        #     # await self._warp_in_queue.put(
        #     #     (WarpInTaskResult.WARNING, f"{len(results)} services are not shutdown")
        #     # )
                
        # await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.DISAPPEARANCE.name}...ok"))
                
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
                timeout = self.node_config.preparation_timeout
            case WarpInPhase.INITIATION:
                timeout = self.node_config.initialization_timeout
                asyncio.create_task(self._initialize_task())
            case WarpInPhase.DISAPPEARANCE:
                timeout = self.node_config.disappearance_timeout
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
        self.create_local_registry()
        internal_health_check = asyncio.create_task(self.internal_health_check(shutdown_event))
        external_node_event = asyncio.create_task(self.external_node_event(shutdown_event))
        external_health_check = asyncio.create_task(self.external_health_check(shutdown_event))
        try:
            yield self
        finally:
            await self.arbiter.broker.broadcast("ARBITER.NODE", self.registry.local_node.get_id(), "NODE_DISCONNECT")
            await asyncio.to_thread(self._internal_mp_queue.put, obj="exit")
            internal_health_check.cancel()
            external_node_event.cancel()
            external_health_check.cancel()
            # TODO task health            
            await self.clear()

    def failed_nodes(self, node_ids: list[str]) -> None:
        # external health check에서 확인하여 제거하는 것이 정확 할 것 같다
        for node_id in node_ids:
            self.registry.unregister_node(node_id)
            self.registry.unregister_service_node(node_id)
            self.registry.unregister_task_node(node_id)
            self.registry.failed_health_signal(node_id)
    
    async def external_health_check(self, shutdown_event: asyncio.Event):
        try:
            while not shutdown_event.is_set():
                await self.arbiter.broker.broadcast(
                    "ARBITER.NODE", 
                    self.registry.local_node.get_id(),
                    "NODE_HEALTH")
                now = time.time()
                node_ids: list[str] = []
                for node_id, received_time in self.registry.node_health.items():
                    if received_time + self.node_config.external_health_check_timeout < now:
                        print("failed external health check", node_id)
                        node_ids.append(node_id)
                self.failed_nodes(node_ids)
                await asyncio.sleep(self.node_config.external_health_check_interval)
        except Exception as err:
            print('failed external health checok', err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()

    async def internal_health_check(self, shutdown_event: asyncio.Event):
        try:
            while not shutdown_event.is_set():
                receive = await asyncio.to_thread(
                    self._internal_mp_queue.get, 
                    timeout=self.node_config.internal_health_check_timeout)
        except (Exception, TimeoutError) as err:
            print("failed internal health check")
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()

    async def external_node_event(self, shutdown_event: asyncio.Event):
        try:
            subject = "ARBITER.NODE"
            await self.arbiter.broker.broadcast(subject, self.registry.raw_node_info, "NODE_CONNECT")
            async for reply, message in self.arbiter.broker.listen(subject):
                # node_id 혹은 node 임시이기 때문에 정해야한다
                message: str | dict[
                    str, ArbiterNodeModel, ArbiterServiceNode, ArbiterTaskNode
                ] = pickle.loads(message)
                match reply:
                    case "NODE_CONNECT":
                        """It will execute when first connect with same broker"""
                        peer_node = message['node']
                        peer_service_node = message['service']
                        peer_task_node = message['task']
                        peer_node_id = peer_node.get_id()
                        local_node_id = self.registry.local_node.get_id()
                        if not self.registry.get_node(peer_node_id) and peer_node_id != local_node_id:
                            self.registry.register_node(peer_node)
                            self.registry.register_service_node(peer_node_id, peer_service_node)
                            self.registry.register_task_node(peer_node_id, peer_task_node)
                            # Peer Node에게도 나의 node 정보를 보내줘야한다
                            await self.arbiter.broker.broadcast(subject, self.registry.raw_node_info, "NODE_CONNECT")
                    case "NODE_UPDATE":
                        """reload app, cover over exist peer id node info"""
                        peer_node = message['node']
                        peer_service_node = message['service']
                        peer_task_node = message['task']
                        self.registry.register_node(peer_node)
                        self.registry.register_service_node(peer_node_id, peer_service_node)
                        self.registry.register_task_node(peer_node_id, peer_task_node)
                    case "NODE_HEALTH":
                        peer_node_id = message
                        if peer_node_id == self.registry.local_node.get_id():
                            continue
                        self.registry.get_health_signal(peer_node_id, time.time())
                    case "NODE_DISCONNECT":
                        """remove registry"""
                        print("disconneced node -", message)

        except Exception as err:
            print("failed external node event", err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()

# atexit.register(arbiter.clear)
# signal.signal(signal.SIGINT, lambda sig,
#               frame: asyncio.create_task(arbiter.shutdown()))