from __future__ import annotations
import asyncio
import uvicorn
import pickle
import timeit
from dataclasses import dataclass
from fastapi import FastAPI
from multiprocessing import Queue as MPQueue
from multiprocessing import Event, Process
from multiprocessing.synchronize import Event as MPEvent
from contextlib import asynccontextmanager
from warnings import warn
from typing import AsyncGenerator, Callable
from arbiter import Arbiter
from arbiter.registry import Registry
from arbiter.registry.gateway import register_gateway
from arbiter.data.models import (
    ArbiterNode as ArbiterNodeModel,
    ArbiterTaskNode,
)
from arbiter.enums import (
    ExternalNodeEvent,
    WarpInTaskResult,
    WarpInPhase,
    NodeState,
)
from arbiter.task_register import TaskRegister
from arbiter.configs import ArbiterNodeConfig, ArbiterConfig
from arbiter.task import ArbiterAsyncTask
from arbiter.task.gateway import ArbiterGateway
from arbiter.task_register import TaskRegister
from arbiter.constants import EXTERNAL_EVENT_SUBJECT
from arbiter.utils import check_queue_and_exit

ArbiterProcess = tuple[Process, MPEvent]

@dataclass
class ExternalEvent:
    event: ExternalNodeEvent
    peer_node_id: str | None = None
    data: ArbiterNodeModel | ArbiterTaskNode | None = None

class ArbiterNode(TaskRegister):
    
    def __init__(
        self,
        *,
        arbiter_config: ArbiterConfig,
        node_config: ArbiterNodeConfig = ArbiterNodeConfig(),
        gateway: FastAPI | uvicorn.Config | None = FastAPI(),
        log_level: str | None = None,
        log_format: str | None = None
    ):
        assert node_config.external_health_check_interval <= 1, "External health check interval must be less than 1"
        self.arbiter_config = arbiter_config
        self.node_config = node_config

        self.arbiter = Arbiter(arbiter_config)
        self.registry = Registry(self.name)
        if isinstance(gateway, FastAPI):
            gateway = uvicorn.Config(app=gateway)
        elif isinstance(gateway, uvicorn.Config):
            assert gateway.app is not None, "Config's app must be provided"
            gateway = gateway
        else:
            gateway = None
            
        gateway and register_gateway(self.name, gateway)
    
        self.log_level = log_level
        self.log_format = log_format
        
        self.is_alive_event = asyncio.Event()
        self.ready_to_listen_external_event = asyncio.Event()

        self._tasks: list[ArbiterAsyncTask] = []
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        self._external_broadcast_queue: asyncio.Queue[tuple[ExternalEvent, bool]] = asyncio.Queue()
        self._external_emit_queue: asyncio.Queue[tuple[str, ExternalEvent]] = asyncio.Queue()
        
        self._arbiter_processes: dict[str, ArbiterProcess] = {}
        self._gateway_process: ArbiterProcess | None = None
        self._internal_health_check_queue: MPQueue = MPQueue()
        self._internal_event_queue: MPQueue = MPQueue()

    @property
    def name(self) -> str:
        return self.arbiter.arbiter_config.name
    
    @property
    def node_id(self) -> str:
        return self.registry.local_node.get_id()
    
    def trace(self, **kwargs) -> Callable:
        def decorator(func: Callable):
            # ArbiterAsyncTask 인스턴스 생성 및 등록
            # find task who has func
            if not self._tasks:
                raise ValueError("No task registered")
            for task in self._tasks:
                if task.func == func:
                    task.trace(**kwargs)
                    break
            return func
        return decorator
    
    def regist_task(self, task: ArbiterAsyncTask):
        self._tasks.append(task)

    def _start_gateway_process(self) -> ArbiterProcess:
        event = Event()
        process = Process(
            target=ArbiterGateway().run,
            args=(
                event,
                self.arbiter_config,
                self.registry.http_tasks,
                self.node_config.gateway_health_check_interval
            )
        )
        process.start()
        return process, event
    
    def _refresh_gateway_process(self):
        if self._gateway_process:
            process, event = self._gateway_process
            if process.is_alive():
                event.set()
            try:
                process.join(timeout=self.node_config.service_disappearance_timeout)
            except Exception as e:
                warn(f"Failed to stop gateway with {e}")
                process.terminate()
        self._gateway_process = self._start_gateway_process()

    def _start_task_process(self, task: ArbiterAsyncTask) -> ArbiterProcess:
        event = Event()
        process = Process(
            target=task.run,
            args=(
                self._internal_health_check_queue,
                self._internal_event_queue,
                event,
                self.arbiter_config,
                self.node_config.service_health_check_interval,
                self.node_config.task_close_timeout
            )
        )
        process.start()
        self.registry.create_local_task_node(task.node)
        return process, event

    async def _preparation_task(self):
        """
            만들기 전에 검사하는 단계라고 생각하면 될까?
            Process를 만든다?
            1차 유효성 검증 후 registry 채널에 등록 요청 한다.
        """        
        try:
            # default task가 있다면 서비스를 하나 만들어야 한다..?
            # ArbiterNode에 등록된 하위 노드의 process 객체를 생성한다
            for task in self._tasks:
                self._arbiter_processes[task.node.node_id] = self._start_task_process(task)
        except Exception as e:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL,
                 f"{WarpInPhase.PREPARATION.name}...service {task.queue} failed to start"))
            return
                
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        
        return

    async def _initialize_task(self):
        def get_active_tasks() -> list[ArbiterTaskNode]:
            return [
                node 
                for node in self.registry.local_task_node
                if node.state == NodeState.ACTIVE
            ]
        start = timeit.default_timer()
        while len(self._tasks) != len(get_active_tasks()):
            await asyncio.sleep(0.01)
            # start_phase에서 발생하는 에러를 피하기 위해 타임아웃을 더 작게 설정한다(이후에 task 상태가 변할 수 있기 때문)
            if timeit.default_timer() - start >= self.node_config.initialization_timeout - 1:
                self._warp_in_queue.put_nowait((
                    WarpInTaskResult.FAIL,
                    f"{WarpInPhase.INITIATION.name} some task didn't launched"))
                return
    
        # 처음에 노드의 모든 정보를 보낸다
        # task가 정상/비정상이든 일단 보낸다 deprecated
        # task로부터 state 혹은 parameter가 업데이트되면 다시 보내서 peer node가 업데이트 할 수 있도록 한다
        self.ready_to_listen_external_event.set()

        await self._external_broadcast_queue.put((
            ExternalEvent(
                event=ExternalNodeEvent.NODE_CONNECT,
                data=self.registry.local_node,
            ), False))
 
        await self._external_broadcast_queue.put((
            ExternalEvent(
                event=ExternalNodeEvent.TASK_UPDATE,
                data=get_active_tasks(),
            ), True))
        
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
       
    async def _disappearance_task(self):
        """
            WarpInPhase Arbiter DISAPPEARANCE
        """       
        for service_node_id, (process, event) in self._arbiter_processes.items():
            if process.is_alive():
                event.set()

        for service_node_id, (process, event) in self._arbiter_processes.items():
            try:
                process.join(timeout=self.node_config.service_disappearance_timeout)
            except Exception as e:
                warn(f"Failed to stop service {service_node_id} with {e}")
                process.terminate()
                
        if self._gateway_process:
            process, event = self._gateway_process
            if process.is_alive():
                event.set()
            try:
                process.join(timeout=self.node_config.service_disappearance_timeout)
            except Exception as e:
                warn(f"Failed to stop gateway with {e}")
                process.terminate()
  
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.DISAPPEARANCE.name}...ok"))
          
    async def start_phase(self, phase: WarpInPhase) -> AsyncGenerator[tuple[WarpInTaskResult, str], None]:
        # if warp_in_queue is empty, then start the phase
        if not self._warp_in_queue.empty():
            warn('Warp In Queue is not empty')
            # remove all messages in the queue
            while not self._warp_in_queue.empty():
                print("remove message", self._warp_in_queue.get_nowait())
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
        shutdown_event: MPEvent,
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

        external_broadcast_task = asyncio.create_task(self.external_broadcast_task())
        external_emit_task = asyncio.create_task(self.external_emit_task())
        external_node_event = asyncio.create_task(self.external_node_event())
        external_event_listener = asyncio.create_task(self.external_event_listener(shutdown_event))
        external_health_check = asyncio.create_task(self.external_health_check(shutdown_event))
        gateway_reload_task = asyncio.create_task(self.gateway_reload_task(shutdown_event))
        
        loop = asyncio.get_running_loop()
        internal_health_check = loop.run_in_executor(None, self.internal_health_check, shutdown_event)
        internal_event = loop.run_in_executor(None, self.internal_event, shutdown_event)

        try:
            yield self
        except Exception as e:
            # TODO logging
            print("Raise error in warp - in", e)
        finally:
            await self._external_broadcast_queue.put((
                ExternalEvent(
                    event=ExternalNodeEvent.NODE_DISCONNECT), False))
            self._external_broadcast_queue.put_nowait((None, None))
            self._external_emit_queue.put_nowait((None, None))
            if not await check_queue_and_exit(
                self._external_broadcast_queue, 
                self.node_config.disappearance_timeout):
                # TODO logging
                print("Failed to empty broadcast queue")
            
            if not await check_queue_and_exit(
                self._external_emit_queue, 
                self.node_config.disappearance_timeout):
                print("Failed to empty emit queue")

            shutdown_event.set()
            await asyncio.to_thread(self._internal_health_check_queue.put, obj="exit")
            gateway_reload_task.cancel()
            external_broadcast_task.cancel()
            external_emit_task.cancel()            
            external_event_listener.cancel()
            external_node_event.cancel()
            external_health_check.cancel()
            internal_health_check.cancel()
            internal_event.cancel()
            self.registry.clear()
            self._arbiter_processes.clear()
            self.arbiter and await self.arbiter.disconnect()

    def internal_event(self, shutdown_event: MPEvent):
        """
        NODE 와 TASK NODE와 통신하는 내부 이벤트 큐
        internal_event_timeout은 sleep 효과를 주기 위해 사용한다
        따로 종료 이벤트가 없다.
        """
        while not shutdown_event.is_set():
            try:
                node_info: dict[str, str] = self._internal_event_queue.get(
                    timeout=self.node_config.internal_event_timeout)
                          
                self.registry.update_local_task_node(node_info)
                # print("internal event", node_info)
                # TODO broadcast to all nodes
                # update task node state or create task node
                # if create task node, and has gateway, then add to gateway
                # and refresh gateway
            except Exception as err:
                """ignore timeout error"""

    def internal_health_check(self, shutdown_event: MPEvent):
        """
        NODE 에서 하위 TASK NODE의 HEALTH CHECK를 수행한다
        현재 NODE에서 동작하고 있는 TASK NODE가 없다면, 현재는 스스로 종료하게 한다.
        """
        try:
            while not shutdown_event.is_set():
                receive = self._internal_health_check_queue.get(
                    timeout=self.node_config.internal_health_check_timeout
                )
        except (Exception, TimeoutError) as err:
            print("failed internal health check", err)
        finally:
            self.is_alive_event.set()

    async def gateway_reload_task(self, shutdown_event: MPEvent):
        try:
            await self.ready_to_listen_external_event.wait()
            while not shutdown_event.is_set():
                if self.registry.check_gateway_reload():
                    self._refresh_gateway_process()
                await asyncio.sleep(self.node_config.gateway_refresh_interval)
        except Exception as err:
            print('failed external health check', err)
        finally:
            self.is_alive_event.set()
            
    async def external_broadcast_task(self):
        while True:
            event, reply = await self._external_broadcast_queue.get()
            if event is None:
                break
            event.peer_node_id = self.registry.local_node.get_id()
            await self.arbiter.broker.broadcast(
                EXTERNAL_EVENT_SUBJECT,
                event,
                event.peer_node_id if reply else None)
            self._external_broadcast_queue.task_done()
        self._external_broadcast_queue.task_done()    
    async def external_emit_task(self):
        while True:
            target, event = await self._external_emit_queue.get()
            if event is None:
                break
            event.peer_node_id = self.registry.local_node.get_id()
            await self.arbiter.broker.emit(target, event)
            self._external_emit_queue.task_done()
        self._external_emit_queue.task_done()
            
    async def external_event_listener(
        self, 
        shutdown_event: MPEvent
    ):
        try:
            async for reply, event in self.arbiter.broker.subscribe_listen(self.registry.local_node.get_id()):
                # 만약 종료하라고 메세지가 온다면..?
                # add node to registry
                if not event:
                    continue
                event: ExternalEvent = pickle.loads(event)
                match event.event:
                    case ExternalNodeEvent.NODE_CONNECT:
                        """It will execute when first connect with same broker"""
                        if self.registry.get_node(event.peer_node_id):
                            print("already connected peer node", event.peer_node_id)
                            continue
                        self.registry.register_node(event.data)
                    case ExternalNodeEvent.TASK_UPDATE:
                        self.registry.register_task_node(event.peer_node_id, event.data)
                    case _:
                        # unknown event
                        raise ValueError(f"Unknown ExternalNodeEvenType {event.event}")                    
        except Exception as err:
            print("failed external event listener", err)
        finally:
            self.is_alive_event.set()
        
    async def external_health_check(self, shutdown_event: MPEvent):
        try:
            await self.ready_to_listen_external_event.wait()
            while not shutdown_event.is_set():
                # local registry가 생성된 후 부터 health check가 되어야한다
                await self._external_broadcast_queue.put((
                    ExternalEvent(event=ExternalNodeEvent.NODE_HEALTH_CHECK)
                    , False))
                failed_node_ids = self.registry.check_node_healths(
                    self.node_config.external_health_check_timeout
                )
                if failed_node_ids:
                    pass
                    # print("failed node ids", failed_node_ids)
                    # # get current task queue
                    
                #     # check gateway need to reload
                await asyncio.sleep(self.node_config.external_health_check_interval)
        except Exception as err:
            print('failed external health check', err)
        finally:
            self.is_alive_event.set()

    async def external_node_event(self):
        try:
            await self.ready_to_listen_external_event.wait()
             # TODO udpate subscribe_listen, for other brokers
            async for reply, event in self.arbiter.broker.subscribe_listen(EXTERNAL_EVENT_SUBJECT):
                # node_id 혹은 node 임시이기 때문에 정해야한다
                event: ExternalEvent = pickle.loads(event)   
                if event.peer_node_id == self.registry.local_node.get_id():
                    # ignore local node
                    continue
                # print("external event", event.event)
                match event.event:
                    case ExternalNodeEvent.NODE_CONNECT:
                        """It will execute when first connect with same broker"""
                        if self.registry.get_node(event.peer_node_id):
                            print("already connected peer node", event.peer_node_id)
                            continue
                        self.registry.register_node(event.data)
                        reply and await self._external_emit_queue.put((
                            reply,
                            ExternalEvent(
                                event=ExternalNodeEvent.NODE_CONNECT,
                                data=self.registry.local_node
                            )))
                        # print("connected peer node", event.peer_node_id)
                    case ExternalNodeEvent.NODE_UPDATE:
                        # RAW NODE INFO 
                        pass
                    case ExternalNodeEvent.NODE_HEALTH_CHECK:
                        self.registry.update_health_signal(event.peer_node_id)
                    case ExternalNodeEvent.NODE_DISCONNECT:
                        """remove registry"""
                        self.registry.failed_health_signal(event.peer_node_id)
                        pass
                    case ExternalNodeEvent.TASK_UPDATE:
                        # currently, for task node update
                        # overwrite task node
                        self.registry.register_task_node(event.peer_node_id, event.data)
                        reply and await self._external_emit_queue.put((
                            reply,
                            ExternalEvent(
                                event=ExternalNodeEvent.TASK_UPDATE,
                                data=self.registry.local_task_node)))
                    case ExternalNodeEvent.TASK_STATE_UPDATE:
                        pass
                    case _:
                        # unknown event
                        raise ValueError(f"Unknown ExternalNodeEvenType {event.event}")                    
                
        except Exception as err:
            print("failed external node event", err)
        finally:
            self.is_alive_event.set()
