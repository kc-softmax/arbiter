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
    ArbiterServiceNode,
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
ExternalMessage = str | ArbiterNodeModel | dict[str, ArbiterTaskNode]

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
        
        self._internal_mp_queue: MPQueue = MPQueue()
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
            return task_node
        
        def get_arbiter() -> Arbiter:
            def setup_arbiter(config: ArbiterConfig):
                pass
            # add ar
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
                        self._internal_mp_queue,
                        event,
                        self.arbiter_config,
                        self.node_config.service_health_check_interval
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
            if timeit.default_timer() - start >= self.node_config.initialization_timeout:
                print("some task didn't launched")
                break

        self.ready_to_listen_external_event.set()

        # 처음에 노드의 모든 정보를 보낸다
        # task가 정상/비정상이든 일단 보낸다
        # task로부터 state 혹은 parameter가 업데이트되면 다시 보내서 peer node가 업데이트 할 수 있도록 한다
        await self.arbiter.broker.broadcast("ARBITER.NODE", self.registry.local_node, "NODE_CONNECT")
        await self.arbiter.broker.broadcast("ARBITER.NODE", self.registry.local_task_node, "TASK_UPDATE")
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
       
    async def _materialization_task(self):
        if not self.gateway:
            await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.MATERIALIZATION.name}...ok"))
            return
        for task in self._tasks:
            if not isinstance(task, ArbiterHttpTask):
                continue
            try:
                self.add_http_task_to_gateway(task.node)
            except Exception as e:
                await self._warp_in_queue.put(
                    (WarpInTaskResult.WARNING,
                     f"{WarpInPhase.MATERIALIZATION.name} Failed to add task to gateway {task.queue} with {e}"))
                continue

        await self._warp_in_queue.put((WarpInTaskResult.SUCCESS, f"{WarpInPhase.MATERIALIZATION.name}...ok"))
        return       
    
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
        return
          
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
            case WarpInPhase.MATERIALIZATION:
                timeout = self.node_config.materialization_timeout
                asyncio.create_task(self._materialization_task())
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
        external_node_event = asyncio.create_task(self.external_node_event(shutdown_event))
        external_health_check = asyncio.create_task(self.external_health_check(shutdown_event))

        loop = asyncio.get_running_loop()
        internal_health_check = loop.run_in_executor(None, self.internal_health_check, shutdown_event)
        try:
            yield self
        except Exception as e:
            # TODO logging
            print("Raise error in warp - in", e)
        finally:
            await self.arbiter.broker.broadcast("ARBITER.NODE", self.registry.local_node.get_id(), "NODE_DISCONNECT")
            await asyncio.to_thread(self._internal_mp_queue.put, obj="exit")
            internal_health_check.cancel()
            external_node_event.cancel()
            external_health_check.cancel()
            self.clear()
            # TODO task health            
            
            self.arbiter and await self.arbiter.disconnect()            

    def failed_nodes(self, node_ids: list[str]) -> None:
        # external health check에서 확인하여 제거하는 것이 정확 할 것 같다
        for node_id in node_ids:
            self.registry.unregister_node(node_id)
            self.registry.unregister_task_node(node_id)
            self.registry.failed_health_signal(node_id)

    def internal_health_check(self, shutdown_event: asyncio.Event):
        try:
            while not shutdown_event.is_set():
                receive: str | ArbiterTaskNode = self._internal_mp_queue.get(
                    timeout=self.node_config.internal_health_check_timeout
                )
                if isinstance(receive, ArbiterTaskNode):
                    self.registry.create_local_task_node(receive)
        except (Exception, TimeoutError) as err:
            print("failed internal health check", err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()

    async def external_health_check(self, shutdown_event: asyncio.Event):
        try:
            await self.ready_to_listen_external_event.wait()
    
            while not shutdown_event.is_set():
                # local registry가 생성된 후 부터 health check가 되어야한다
                if self.registry.local_node:
                    await self.arbiter.broker.broadcast(
                        "ARBITER.NODE", 
                        self.registry.local_node.get_id(),
                        "NODE_HEALTH")

                # validate check node
                now = time.time()
                node_ids: list[str] = []
                for node_id, received_time in self.registry.node_health.items():
                    if received_time + self.node_config.external_health_check_timeout < now:
                        print("failed external health check", node_id)
                        node_ids.append(node_id)
                self.failed_nodes(node_ids)

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
            async for reply, message in self.arbiter.broker.listen(subject):
                # node_id 혹은 node 임시이기 때문에 정해야한다
                node: ExternalMessage = pickle.loads(message)
                match reply:
                    case "NODE_CONNECT":
                        """It will execute when first connect with same broker"""
                        peer_node_id = node.get_id()
                        local_node_id = self.registry.local_node.get_id()
                        if not self.registry.get_node(peer_node_id) and peer_node_id != local_node_id:
                            self.registry.register_node(node)
                            # Peer Node에게도 나의 node 정보를 보내줘야한다
                            await self.arbiter.broker.broadcast(subject, self.registry.local_node, "NODE_CONNECT")
                            print("connected peer node", peer_node_id)
                    case "NODE_UPDATE":
                        """reload app, cover over exist peer id node info"""
                    case "TASK_UPDATE":
                        """receive task node, cover over exist peer id task node info"""
                    case "NODE_HEALTH":
                        peer_node_id = node
                        self.registry.get_health_signal(peer_node_id, time.time())
                    case "NODE_DISCONNECT":
                        """remove registry"""
                        print("disconnected peer node -", node)

        except Exception as err:
            print("failed external node event", err)
            self.internal_shutdown_event.set()
        finally:
            self.stop_gateway()
            shutdown_event.set()