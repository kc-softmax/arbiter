from __future__ import annotations
import asyncio
import io
import json
import time
import uuid
import uvicorn
import pickle
import timeit
from multiprocessing import Queue as MPQueue
from multiprocessing import Event
from multiprocessing import Process
# from aiomultiprocess import Process
from multiprocessing.synchronize import Event as EventType
from contextlib import asynccontextmanager
from warnings import warn
from typing import (
    AsyncGenerator,
    Callable,
    Type,
    Any
)
from pydantic import create_model, BaseModel
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Depends, HTTPException, Request
from arbiter import Arbiter
from arbiter.exceptions import TaskBaseError
from arbiter.registry import Registry
from arbiter.data.models import (
    ArbiterNode as ArbiterNodeModel,
    ArbiterTaskNode,
)
from arbiter.enums import (
    WarpInTaskResult,
    WarpInPhase,
    NodeState,
)
from arbiter.task_register import TaskRegister
from arbiter.configs import ArbiterNodeConfig, ArbiterConfig
from arbiter.task import ArbiterAsyncTask, ArbiterHttpTask
from arbiter.task_register import TaskRegister
from arbiter.utils import restore_type

ArbiterProcess = tuple[Process, EventType]
ExternalMessage = str | ArbiterNodeModel | dict[str, ArbiterNodeModel | ArbiterTaskNode] | list[ArbiterTaskNode]

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
        
        if isinstance(gateway, FastAPI):
            self.gateway_config = uvicorn.Config(app=gateway)
            self.gateway_server = uvicorn.Server(self.gateway_config)
            self.gateway = gateway
        elif isinstance(gateway, uvicorn.Config):
            assert gateway.app is not None, "Config's app must be provided"
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
        self.ready_to_listen_external_event = asyncio.Event()
        self.arbiter = Arbiter(arbiter_config)
        self.registry: Registry = Registry()

        self._tasks: list[ArbiterAsyncTask] = []
        self._warp_in_queue: asyncio.Queue = asyncio.Queue()
        self._arbiter_processes: dict[str, ArbiterProcess] = {}
        
        self._internal_health_check_queue: MPQueue = MPQueue()
        self._internal_event_queue: MPQueue = MPQueue()
        self._deafult_tasks: list[ArbiterAsyncTask] = []

    def clear(self):
        self.registry.clear()
        self._arbiter_processes.clear()
        self.internal_shutdown_event.clear()
        self.ready_to_listen_external_event.clear()

    @property
    def name(self) -> str:
        return self.arbiter.arbiter_config.name
    
    def regist_task(self, task: ArbiterAsyncTask):
        self._tasks.append(task)
        
    def start_gateway(self, shutdown_event: asyncio.Event) -> asyncio.Task:
        async def _gateway_loop():
            while not shutdown_event.is_set():
                for http_task in self.registry.all_active_http_tasks:
                    self.add_http_task_to_gateway(http_task)
                self.registry.http_reload = False
                self.gateway_server.should_exit = False
                await self.gateway_server.serve()
                # TODO 1초면 종료 다 할 수 있나? 다른 
                await asyncio.sleep(1)
        return asyncio.create_task(_gateway_loop())
    
    def stop_gateway(self):
        if self.gateway_server:
            self.gateway_server.should_exit = True

    def add_http_task_to_gateway(self, task_node: ArbiterTaskNode):
        def get_task_node() -> ArbiterTaskNode:
            # if task_node.state
            return task_node
        
        def get_arbiter() -> Arbiter:
            return self.arbiter

        # TODO routing
        path = f'/{task_node.queue}'
        
        parameters = json.loads(task_node.transformed_parameters)
        assert isinstance(parameters, dict), "Parameters must be dict"
        parameters = {
            k: (restore_type(v), ...)
            for k, v in parameters.items()
        }
        requset_model = create_model(task_node.name, **parameters)
        return_type = restore_type(json.loads(task_node.transformed_return_type))

        # find base model in parameters
        is_post = True if parameters else False
        for _, v in parameters.items():
            if not issubclass(v[0], BaseModel):
                is_post = False
                
        async def arbiter_task(
            request: Request,
            data: Type[BaseModel] = Depends(requset_model),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            arbiter: Arbiter = Depends(get_arbiter),
            task_node: ArbiterTaskNode = Depends(get_task_node),
        ):
            async def stream_response(
                data: BaseModel,
                arbiter: Arbiter,
                task_node: ArbiterTaskNode,
            ):
                async def stream_response_generator(data_dict: dict[str, Any]):
                    try:
                        async for results in arbiter.async_stream(
                            target=task_node.queue,
                            **data_dict
                        ):
                            if isinstance(results, Exception):
                                raise results
                            if isinstance(results, BaseModel):
                                yield results.model_dump_json()
                            else:
                                yield results
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"Failed to get response {e}")
                return StreamingResponse(stream_response_generator(data), media_type="application/json")
            
            data_dict: dict = data.model_dump()
            if task_node.request:
                request_data = {
                    'client': request.client,
                    'headers': request.headers,
                    'cookies': request.cookies,
                    'query_params': request.query_params,
                    'path_params': request.path_params,
                }
                data_dict.update({'request': request_data})
            
            if task_node.stream:
                return await stream_response(data_dict, arbiter, task_node)

            try:
                results = await arbiter.async_task(
                    target=task_node.queue,
                    **data_dict)
                # TODO 어디에서 에러가 생기든, results 받아온다.
                if isinstance(results, Exception):
                    raise results
                
                # TODO temp, 추후 수정 필요
                if task_node.file:
                    if isinstance(results, tuple) or isinstance(results, list):
                        filename, file = results
                    else:
                        file = results
                        # get file extension
                        filename = uuid.uuid4().hex
                    # filename, file = results
                    file_like = io.BytesIO(file)
                    headers = {
                        "Content-Disposition": f"attachment; filename={filename}",
                        }
                    return StreamingResponse(file_like, media_type="application/octet-stream", headers=headers)
                if isinstance(results, BaseModel):
                    return results.model_dump()                
                return results
            except TaskBaseError as e:
                raise e
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to get response {e}")

        if is_post:
            self.gateway.router.post(
                path,
                response_model=return_type
            )(arbiter_task)
        else:
            self.gateway.router.get(
                path,
                response_model=return_type
            )(arbiter_task)

    def create_local_registry(self):
        # 자신의 registry는 local_node로 관리한다
        arbiter_node = ArbiterNodeModel(
            name=self.name,
            state=NodeState.ACTIVE
        )
        self.registry.create_local_node(arbiter_node)

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
                event = Event()
                process = Process(
                    name=task.queue,
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
                self._arbiter_processes[task.node.node_id] = (process, event)
        except Exception as e:
            await self._warp_in_queue.put(
                (WarpInTaskResult.FAIL,
                 f"{WarpInPhase.PREPARATION.name}...service {task.queue} failed to start"))
            return
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.PREPARATION.name}...ok"))
        return

    async def _initialize_task(self):
        """
            WarpInPhase Arbiter initialization
        """

        # initialize된 상태에 대해 어떻게 할 것인가?
        # node를 초기화한다
        # task node에 대한 health check를 모두 통과해야한다
        self.create_local_registry()

        # 문제가있는 task는 버리고 갈지 에러를 낼지 생각해봐야한다
        start = timeit.default_timer()
        while len(self._tasks) != len(self.registry.local_task_node):
            await asyncio.sleep(0.01)
            # start_phase에서 발생하는 에러를 피하기 위해 타임아웃을 더 작게 설정한다(이후에 task 상태가 변할 수 있기 때문)
            if timeit.default_timer() - start >= self.node_config.initialization_timeout - 1:
                self._warp_in_queue.put_nowait((
                    WarpInTaskResult.FAIL,
                    f"{WarpInPhase.INITIATION.name} some task didn't launched"))
                break

        self.ready_to_listen_external_event.set()

        # 처음에 노드의 모든 정보를 보낸다
        # task가 정상/비정상이든 일단 보낸다
        # task로부터 state 혹은 parameter가 업데이트되면 다시 보내서 peer node가 업데이트 할 수 있도록 한다
        await self.arbiter.broker.broadcast(
            "ARBITER.NODE",
            self.registry.raw_node_info,
            "NODE_CONNECT"
        )
        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.INITIATION.name}...ok"))
        self.gateway_reload = True
       
    async def _disappearance_task(self):
        """
            WarpInPhase Arbiter DISAPPEARANCE
            stop all web service with ternimate gunicorn process
            
            if master
                broadcast shutdown message to all nodes
            broadcast shutdown message to all services in node
            check database            
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
        if self.gateway:
            gateway_event = asyncio.create_task(self.gateway_event(shutdown_event))
        else:
            gateway_event = None

        external_node_event = asyncio.create_task(self.external_node_event(shutdown_event))
        external_health_check = asyncio.create_task(self.external_health_check(shutdown_event))

        loop = asyncio.get_running_loop()
        internal_health_check = loop.run_in_executor(None, self.internal_health_check, shutdown_event)
        internal_event = loop.run_in_executor(None, self.internal_event, shutdown_event)
        try:
            yield self
        except Exception as e:
            # TODO logging
            print("Raise error in warp - in", e)
        finally:
            await self.arbiter.broker.broadcast(
                "ARBITER.NODE",
                self.registry.local_node.get_id(),
                "NODE_DISCONNECT")
            await asyncio.to_thread(self._internal_health_check_queue.put, obj="exit")
            gateway_event and gateway_event.cancel()
            internal_health_check.cancel()
            internal_event.cancel()
            external_node_event.cancel()
            external_health_check.cancel()
            self.clear()            
            self.arbiter and await self.arbiter.disconnect()

    def internal_event(self, shutdown_event: asyncio.Event):
        while not shutdown_event.is_set():
            try:
                node_info: ArbiterTaskNode | dict[str, str] = self._internal_event_queue.get(
                    timeout=self.node_config.internal_event_timeout)
                target = "ARBITER.NODE"
                
                if isinstance(node_info, ArbiterTaskNode):
                    self.registry.create_local_task_node(node_info)
                else:
                    self.registry.update_local_task_node(node_info)
                # TODO broadcast to all nodes
                # update task node state or create task node
                # if create task node, and has gateway, then add to gateway
                # and refresh gateway
            except Exception as err:
                """ignore timeout error"""

    def internal_health_check(self, shutdown_event: asyncio.Event):
        try:
            while not shutdown_event.is_set():
                receive = self._internal_health_check_queue.get(
                    timeout=self.node_config.internal_health_check_timeout
                )
        except (Exception, TimeoutError) as err:
            print("failed internal health check", err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()

    async def gateway_event(self, shutdown_event: asyncio.Event):
        try:
            await self.ready_to_listen_external_event.wait()
            while not shutdown_event.is_set():
                if self.registry.http_reload:
                    self.stop_gateway()                    
                await asyncio.sleep(self.node_config.gateway_health_check_interval)
        except Exception as err:
            print("failed gateway event", err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()

    async def external_health_check(self, shutdown_event: asyncio.Event):
        try:
            await self.ready_to_listen_external_event.wait()
    
            while not shutdown_event.is_set():
                # local registry가 생성된 후 부터 health check가 되어야한다
                # if self.registry.local_node:
                await self.arbiter.broker.broadcast(
                    "ARBITER.NODE", 
                    self.registry.local_node.get_id(),
                    "NODE_HEALTH")

                # validate check node
                failed_node_ids = self.registry.check_node_healths(
                    self.node_config.external_health_check_timeout
                )

                if failed_node_ids:
                    # check gateway need to reload
                    self.gateway_reload = True
                
                await asyncio.sleep(self.node_config.external_health_check_interval)
        except Exception as err:
            print('failed external health check', err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()

    async def external_node_event(self, shutdown_event: asyncio.Event):
        try:
            await self.ready_to_listen_external_event.wait()

            subject = "ARBITER.NODE"
             # TODO udpate subscribe_listen, for other brokers
            async for reply, message in self.arbiter.broker.listen(subject):
                # node_id 혹은 node 임시이기 때문에 정해야한다
                node: ExternalMessage = pickle.loads(message)
                match reply:
                    case "NODE_CONNECT":
                        """It will execute when first connect with same broker"""
                        arbiter_node = node['node']
                        task_nodes = node['task']
                        peer_node_id = arbiter_node.get_id()
                        local_node_id = self.registry.local_node.get_id()
                        # 이미 등록된 노드가 아니고, 자신의 노드가 아닌 경우에만 등록한다
                        if not self.registry.get_node(peer_node_id) and peer_node_id != local_node_id:
                            self.registry.register_node(arbiter_node)
                            self.registry.register_task_node(peer_node_id, task_nodes)
                            # Peer Node에게도 나의 node 정보를 보내줘야한다
                            await self.arbiter.broker.broadcast(subject, self.registry.raw_node_info, "NODE_CONNECT")
                            self.gateway_reload = True
                            print("connected peer node", peer_node_id)
                    case "NODE_UPDATE":
                        """reload app, cover over exist peer id node info"""
                        self.gateway_reload = True
                    case "TASK_UPDATE":
                        # print("update peer task node -", node)
                        for _node in node:
                            self.registry.register_task_node(_node.get_id(), _node)
                        self.gateway_reload = True
                        """receive task node, cover over exist peer id task node info"""
                    case "NODE_HEALTH":
                        peer_node_id = node
                        self.registry.update_health_signal(peer_node_id)
                    case "NODE_DISCONNECT":
                        """remove registry"""
                        self.registry.failed_health_signal(node)
                        print("disconnected peer node -", node)

        except Exception as err:
            print("failed external node event", err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()
