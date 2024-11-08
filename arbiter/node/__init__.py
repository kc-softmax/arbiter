from __future__ import annotations
import asyncio
import uvicorn
import pickle
from dataclasses import dataclass
from fastapi import FastAPI
from contextlib import asynccontextmanager
from warnings import warn
from typing import AsyncGenerator, Callable
from arbiter import Arbiter
from arbiter.registry import NodeRegistry
from arbiter.data.models import ArbiterNodeModel, ArbiterTaskModel
from arbiter.enums import (
    EventType,
    WarpInTaskResult,
    WarpInPhase,
    ModelState,
)
from arbiter.task_register import TaskRegister
from arbiter.configs import ArbiterNodeConfig, NatsArbiterConfig
from arbiter.task import ArbiterAsyncTask
from arbiter.task_register import TaskRegister
from arbiter.constants import EXTERNAL_EVENT_SUBJECT
from arbiter.logger import ArbiterLogger
from arbiter.utils import check_queue_and_exit, find_variables_with_annotation

@dataclass
class EventMessage:
    event: EventType
    peer_node_id: str | None = None
    data: ArbiterNodeModel | None = None

class ArbiterNode(TaskRegister):
    
    def __init__(
        self,
        *,
        arbiter_config: NatsArbiterConfig = NatsArbiterConfig(),
        node_config: ArbiterNodeConfig = ArbiterNodeConfig(),
        gateway: FastAPI | uvicorn.Config | None = FastAPI(),
    ):
        assert node_config.external_health_check_interval <= 1, "External health check interval must be less than 1"
        self.arbiter_config = arbiter_config
        self.node_config = node_config

        self.arbiter = Arbiter(arbiter_config)
        self.registry = NodeRegistry()
        self.node_model = ArbiterNodeModel(name=self.name)
        self.task_models: list[ArbiterTaskModel] = []
        if isinstance(gateway, FastAPI):
            gateway = uvicorn.Config(app=gateway)
        elif isinstance(gateway, uvicorn.Config):
            assert gateway.app is not None, "Config's app must be provided"
            gateway = gateway
        else:
            gateway = None
            
        self.logger = ArbiterLogger(name=self.__class__.__name__)
        self.logger.add_handler()
        
        self._prepare_signal: asyncio.Event = asyncio.Event()
        self._task_status_queue: asyncio.Queue = asyncio.Queue()
        self._arbiter_tasks: list[tuple[asyncio.Queue, asyncio.Task]] = []
        
        self._on_startup: Callable = None
        self._on_shutdown: Callable = None
        self._tasks: list[ArbiterAsyncTask] = []
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()        

    @property
    def name(self) -> str:
        return self.arbiter.arbiter_config.name
    
    @property
    def node_id(self) -> str:
        return self.node_model.get_id()
    
    def on_startup(self):
        def decorator(func: Callable):
            self._on_startup = func
            return func
        return decorator

    def on_shutdown(self):
        def decorator(func: Callable):
            self._on_shutdown = func
            return func
        return decorator
    
    def trace(
        self, 
        request: bool = True,
        responses: bool = True,
        error: bool = True,
        execution_times: bool = True,
        callback: Callable = None,
    ) -> Callable:
        def decorator(func: Callable):
            # ArbiterAsyncTask 인스턴스 생성 및 등록
            # find task who has func
            if not self._tasks:
                raise ValueError("No task registered")
            for task in self._tasks:
                if task.func == func:
                    task.trace(
                        request=request,
                        responses=responses,
                        error=error,
                        execution_times=execution_times,
                        callback=callback
                    )
                    break
            return func
        return decorator
    
    def regist_task(self, task: ArbiterAsyncTask):
        self._tasks.append(task)

    async def _preparation_task(self):
        """
            만들기 전에 검사하는 단계라고 생각하면 될까?
            Process를 만든다?
            1차 유효성 검증 후 registry 채널에 등록 요청 한다.
        """
        for task in self._tasks:
            try:
                message_queue = asyncio.Queue()
                self._arbiter_tasks.append(
                    (
                        message_queue,
                        asyncio.create_task(
                            task.run(
                                self.arbiter_config,
                                self._task_status_queue,
                                message_queue,
                            )
                        )
                    )
                )
                self.task_models.append(task.task_model)
            except Exception as e:
                await self._warp_in_queue.put(
                    (WarpInTaskResult.FAIL, f"{WarpInPhase.PREPARATION.name}...service {task.queue} failed to start {e}"))
                return
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        return

    async def _initialize_task(self):
        self._prepare_signal.set()
        await self.arbiter.broker.broadcast(
            EXTERNAL_EVENT_SUBJECT,
            EventMessage(
                event=EventType.NODE_CONNECT,
                data=self.node_model
            ),
            self.node_id
        )
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
        return

    async def _disappearance_task(self):
        """
            WarpInPhase Arbiter DISAPPEARANCE
        """
        for queue, task in self._arbiter_tasks:
            await queue.put(None)
            try:
                await asyncio.wait_for(
                    task,
                    self.node_config.service_disappearance_timeout
                )
            except asyncio.TimeoutError:
                warn(f"Failed to stop service {task} with timeout")
                task.cancel()
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.DISAPPEARANCE.name}...ok"))
        return
   
    async def start_phase(self, phase: WarpInPhase) -> AsyncGenerator[tuple[WarpInTaskResult, str], None]:
        # if warp_in_queue is empty, then start the phase
        if not self._warp_in_queue.empty():
            warn('Warp In Queue is not empty')
            # remove all messages in the queue
            while not self._warp_in_queue.empty():
                self.logger.warning(
                    f"unused warp state message {self._warp_in_queue.get_nowait()}"
                )
                await self._warp_in_queue.get()
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
        interept_event: asyncio.Event,
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
        public_message_queue = asyncio.Queue()
        private_message_queue = asyncio.Queue()

        heartbeat_task = asyncio.create_task(self.heartbeat(interept_event))
        health_check_task = asyncio.create_task(self.health_check())

        public_event_task = asyncio.create_task(self.subscribe_public_event(public_message_queue))
        private_event_task = asyncio.create_task(self.subscribe_private_event(private_message_queue))
        
        try:
            # on stat up
            if self._on_startup:
                find_arbiter_params = find_variables_with_annotation(self._on_startup, Arbiter)
                if find_arbiter_params:
                    assert len(find_arbiter_params) == 1, "Only one Arbiter instance can be passed"
                    params = {param: self.arbiter for param in find_arbiter_params}
                else:
                    params = {}
                if asyncio.iscoroutinefunction(self._on_startup):
                    await self._on_startup(**params)
                else:
                    self._on_startup(**params)

            yield self
            
            if self._on_shutdown:
                find_arbiter_params = find_variables_with_annotation(self._on_shutdown, Arbiter)
                if find_arbiter_params:
                    assert len(find_arbiter_params) == 1, "Only one Arbiter instance can be passed"
                    params = {param: self.arbiter for param in find_arbiter_params}
                else:                
                    params = {}
                if asyncio.iscoroutinefunction(self._on_shutdown):
                    await self._on_shutdown(**params)
                else:
                    self._on_shutdown(**params)
      
        except Exception as e:
            # TODO logging
            self.logger.error(f"Raise error in warp - in {e}")
        finally:
            self._task_status_queue.put_nowait(None)
            public_message_queue.put_nowait(None)
            private_message_queue.put_nowait(None)
            await asyncio.gather(
                public_event_task,
                private_event_task,
                heartbeat_task,
                health_check_task
            )
            self.arbiter and await self.arbiter.disconnect()

    async def health_check(self):
        """
        """
        while True:
            task_status = await self._task_status_queue.get()
            if task_status is None:
                break
            
    async def heartbeat(self, interept_event: asyncio.Event):
        try:
            await self._prepare_signal.wait()
            while not interept_event.is_set():
                await self.arbiter.broker.broadcast(
                    EXTERNAL_EVENT_SUBJECT,
                    EventMessage(
                        event=EventType.NODE_HEALTH_CHECK,
                        peer_node_id=self.node_id
                    )
                )
                removed_ids = self.registry.health_check(
                    self.node_config.external_health_check_timeout
                )
                for removed_id in removed_ids:
                    self.arbiter.task_registry.unregister_tasks(removed_id)
                    
                await asyncio.sleep(self.node_config.external_health_check_interval)
        except Exception as err:
            self.logger.error(f'failed external health check {err}')

    async def subscribe_public_event(
        self,
        message_queue: asyncio.Queue,
    ):
        try:
            await self._prepare_signal.wait()
             # TODO udpate subscribe_listen, for other brokers
            async for reply, event in self.arbiter.broker.subscribe_listen(
                EXTERNAL_EVENT_SUBJECT,
                message_queue
            ):
                # node_id 혹은 node 임시이기 때문에 정해야한다
                event: EventMessage = pickle.loads(event)
                if event.peer_node_id == self.node_id:
                    # ignore self event
                    continue
                match event.event:
                    case EventType.NODE_CONNECT:
                        """It will execute when first connect with same broker"""
                        if self.registry.get_node(event.peer_node_id):
                            self.logger.warning(f"already connected peer node {event.peer_node_id}")
                            continue
                        self.registry.register_node(event.data)
                        # 자신의 노드 정보를 새로생긴 노드에 전달
                        await self.arbiter.broker.emit(
                            reply, EventMessage(
                                event=EventType.NODE_CONNECT,
                                data=self.node_model
                            ))
                        # 자신의 task 정보를 새로생긴 노드에 전달
                        await self.arbiter.broker.emit(
                            reply, EventMessage(
                                event=EventType.TASK_UPDATE,
                                data=self.task_models
                            ))
                    case EventType.NODE_HEALTH_CHECK:
                        self.registry.heartbeat(event.peer_node_id)
                    case EventType.NODE_DISCONNECT:
                        self.registry.disconnect_node(event.peer_node_id)
                    case _:
                        # unknown event
                        raise ValueError(f"Unknown ExternalNodeEvenType {event.event}")                    
                
        except Exception as err:
            self.logger.error(f"failed public event {err}")

    async def subscribe_private_event(
        self,
        message_queue: asyncio.Queue,
    ):
        try:
            async for reply, event in self.arbiter.broker.subscribe_listen(
                self.node_id, 
                message_queue
            ):
                if not event:
                    continue
                event: EventMessage = pickle.loads(event)
                match event.event:
                    case EventType.NODE_CONNECT:
                        """It will execute when first connect with same broker"""
                        if self.registry.get_node(event.peer_node_id):
                            self.logger.warning("already connected peer node", event.peer_node_id)
                            continue
                        self.registry.register_node(event.data)
                    case EventType.TASK_UPDATE:
                        self.arbiter.task_registry.register_tasks(event.peer_node_id, event.data)
                    case _:
                        # unknown event
                        raise ValueError(f"Unknown ExternalNodeEvenType {event.event}")                    
        except Exception as err:
            self.logger.error(f"failed external event listener {err}")
