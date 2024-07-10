from __future__ import annotations
import uuid
import asyncio
import pickle
from configparser import ConfigParser
from fastapi.routing import APIRoute
from uvicorn.workers import UvicornWorker
from typing import Awaitable, Callable, Optional, Union
from fastapi import APIRouter, FastAPI, Query, WebSocket, Depends, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from arbiter.api.auth.router import router as auth_router
from arbiter.api.exceptions import BadRequest
from arbiter.api.stream import ArbiterStream
from arbiter.api.auth.dependencies import get_user
from arbiter.broker import RedisBroker, MessageBrokerInterface
from arbiter.constants.data import ArbiterSystemRequestMessage
from arbiter.constants.enums import ArbiterMessageType
from arbiter.api.auth.utils import verify_token
from arbiter.utils import to_snake_case
from arbiter.database import (
    Database,
    Node,
    TaskFunction,
    User
)
from arbiter.constants.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.constants import (
    ARBITER_API_CHANNEL,
    ARBITER_API_SHUTDOWN_TIMEOUT,
)

"""
Service 처럼 취급해야한다.,
하지만 서비스가 아니다, 나중에 추상화에 도전해볼까?
Health Check, 핑퐁이 아니라, main으로 부터 핑만 받는다?
만약 ping이 오지 않으면, Main App이 죽었다고 판단한다?

마스터가 다운되면, 슬레이브를 마스터로 승격 시켜야 할까?
마스터가 다운되면, 모든 서비스를 다운시켜야 할까?
1번으로 먼저 고민해보자.

API는 task 들을 받을 필요가 있다
따라서 공통의 채널을 구독해야 한다.
"""

ArbiterUvicornWorker = UvicornWorker
ArbiterUvicornWorker.CONFIG_KWARGS = {"loop": "asyncio", "http": "auto"}

class ArbiterApiApp(FastAPI):

    def __init__(
        self,
        config: ConfigParser,
    ) -> None:
        super().__init__()
        self.app_id = uuid.uuid4().hex
        self.add_event_handler("startup", self.on_startup)
        self.add_event_handler("shutdown", self.on_shutdown)
        self.add_exception_handler(
            RequestValidationError,
            lambda request, exc: JSONResponse(
                status_code=BadRequest.STATUS_CODE,
                content={"detail": BadRequest.DETAIL}
            )
        )
        self.add_middleware(
            CORSMiddleware,
            allow_origins=config.get("api", "allow_origins", fallback="*"),
            allow_methods=config.get("api", "allow_methods", fallback="*"),
            allow_headers=config.get("api", "allow_headers", fallback="*"),
            allow_credentials=config.get("api", "allow_credentials", fallback=True),
        )
        # app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)
        self.include_router(auth_router)
        self.db = Database.get_db()
        self.router_task: asyncio.Task = None
        
        self.broker: RedisBroker = RedisBroker()
        
        self.stream_handlers: dict[str, Callable[[
            ArbiterStream], Awaitable[None]]] = {}

    def get_app(self) -> ArbiterApiApp:
        return self

    async def on_startup(self):
        await self.db.connect()
        await self.broker.connect()
        self.router_task = asyncio.create_task(self.router_handler())
        master_nodes = await self.db.search_data(Node, is_master=True)
        assert len(master_nodes) == 1, "There must be only one master node"
        
        await self.broker.send_message(
            master_nodes[0].unique_id,
            ArbiterSystemRequestMessage(
                from_id=self.app_id,
                type=ArbiterMessageType.API_REGISTER,
                ).encode(),
            None)

    async def on_shutdown(self):
        self.router_task and self.router_task.cancel()
        await self.db.disconnect()
        await self.broker.disconnect()

    async def router_handler(self):
        # message 는 어떤 router로 등록해야 하는가?에 따른다?
        # TODO ADD router, remove Router?
        async for message in self.broker.subscribe(ARBITER_API_CHANNEL):
            task_function = TaskFunction.parse_raw(message)
            service_name = task_function.service_meta.name
            
            assert not (
                task_function.method and task_function.connection
            ), "Both method and connection cannot be true at the same time."
            
            # 이미 라우터에 등록되어 있다면 무시한다.
            already_registered = False
            for route in self.routes:
                route: APIRoute
                path = f"/{to_snake_case(service_name)}/{task_function.name}"
                if route.path == path:
                    already_registered = True
                # print(path)
                # print(route.path, route.methods)
                # # if path in router.pat:
                #     # continue
            if already_registered:
                continue
            match task_function.method:
                case HttpMethod.POST:
                    self.generate_post_function(
                        service_name,
                        task_function
                    )
            match task_function.connection:
                case StreamMethod.WEBSOCKET:
                    self.generate_websocket_function(
                        service_name,
                        task_function)

            self.openapi_schema = None

    def generate_post_function(
        self,
        service_name: str,
        task_fuction: TaskFunction,
    ):
        def get_task_fuction() -> TaskFunction:
            return task_fuction
        parameters = ""
        auth_dependency = ""
        for name, type_name in task_fuction.parameters:
            if type_name == "User":
                if not task_fuction.auth:
                    # error 동작 안함
                    raise Exception(
                        "User type parameter is not allowed without auth=True")
                auth_dependency = f"{name}: {type_name} = Depends(get_user), "
            else:
                parameters += f"{name}: {type_name}, "
        if auth_dependency:
            parameters += auth_dependency
        parameters += "app: ArbiterApiApp = Depends(self.get_app), "
        parameters += "task_function: TaskFunction = Depends(get_task_fuction), "
        # Define the function dynamically
        function_definition = f"""
async def {task_fuction.name}({parameters}):
    params = locals()  # Capture the local variables as a dictionary
    params.pop('app')  # Remove the service parameter
    params.pop('task_function')  # Remove the task parameter
    # # Serialize the parameters to bytes
    serialized_params = pickle.dumps(params)
    response = await app.broker.send_message(
        task_function.queue_name,
        serialized_params # Use the serialized bytes
    )
    if not response:
        return {{"message": "Failed to get response"}}
    return {{"message": f"{{response}}"}}
"""
        local_context = {
            'get_user': get_user,
            'get_task_fuction': get_task_fuction,
            'Depends': Depends,
            'Union': Union,
            'User': User,
            'Optional': Optional,
            'self': self
        }
        # Execute the dynamic function definition
        exec(function_definition, globals(), local_context)
        # Retrieve the dynamically defined function
        dynamic_function = local_context[task_fuction.name]
        self.router.post(
            f'/{to_snake_case(service_name)}/{task_fuction.name}',
            tags=[service_name]
        )(dynamic_function)
        
    def generate_websocket_function(
        self,
        service_name: str,
        task_function: TaskFunction,
    ):
        """
            websocket의 경우 parameter가 user 밖에 없을것이다.
            인증방식은 query parameter로 token을 받아서 처리할것이다.
            각각 커뮤니케이션 방식에 따라 동작방식이 다를것이다.
            SYNC_UNICAST
                메세지를 받으면, 처리할때까지 기다리고, 응답을 보낸다. (timeout 이 있다.)
            ASYNC_UNICAST
                메세지를 받으면, 처리하라고 넘기며, 응답은 비동기적으로 보낸다. (time out이 없다.?)
                send message and don't wait for response

            PUSH_NOTIFICATION
            # 로직을 처리하지 않으며, parameter로 channel을 받아서 처리할것이다.?
            
            # 대상은 어떻게 정할것인가?
            # 함수를 만들때 정하지는 못할것이다,
            # '유저가 접속했을때' 그때 정해야 한다. 함수를 dependon으로 받아서 처리해야 한다?
            MULTICAST
                send message to specific group
            BROADCAST
                특정 방에 있는 모두에게 메세지를 보낸다.

        """
        async def handle_async_unicast_websocket(
            websocket: WebSocket,
            user_id: str = None
        ):
            async def get_response(websocket: WebSocket, channel: str):
                async for data in self.broker.listen(channel):
                    await websocket.send_text(data.decode())
                
            websocket_response_ch = uuid.uuid4().hex
            await websocket.accept()

            response_task = asyncio.create_task(get_response(websocket, websocket_response_ch))
            
            try:
                while not response_task.done():
                    receive_data = await websocket.receive_text()
                    if not receive_data:
                        continue
                    data = {
                        "data": receive_data,
                    }
                    if user_id:
                        data["user_id"] = user_id
                    await self.broker.async_send_message(
                        task_function.queue_name,
                        pickle.dumps(data),
                        websocket_response_ch,
                    )
            except WebSocketDisconnect:
                pass
            if not response_task.done():
                response_task.cancel()

        async def handle_sync_unicast_websocket(
            websocket: WebSocket,
            user_id: str = None
        ):
            await websocket.accept()
            try:
                while True:
                    receive_data = await websocket.receive_text()
                    if not receive_data:
                        continue
                    data = {
                        "data": receive_data,
                    }
                    if user_id:
                        data["user_id"] = user_id
                    response = await self.broker.send_message(
                        task_function.queue_name,
                        pickle.dumps(data),
                    )
                    await websocket.send_text(response.decode())
                    
            except WebSocketDisconnect:
                pass

        async def handle_websocket(
            websocket: WebSocket,
            user_id: str = None
        ):
            async def get_response(websocket: WebSocket, channel: str):
                async for data in self.broker.listen(channel):
                    await websocket.send_text(data.decode())
                    
            
            websocket_response_ch = uuid.uuid4().hex
            await websocket.accept()

            response_task = asyncio.create_task(get_response(websocket, websocket_response_ch))
            
            try:
                while not response_task.done():
                    receive_data = await websocket.receive_text()
                    if not receive_data:
                        continue
                    data = {
                        "data": receive_data,
                    }
                    if user_id:
                        data["user_id"] = user_id
                    await self.broker.async_send_message(
                        task_function.queue_name,
                        pickle.dumps(data),
                        websocket_response_ch,
                    )
            except WebSocketDisconnect:
                pass
            if not response_task.done():
                response_task.cancel()

        handle_websocket_functions = {
            StreamCommunicationType.ASYNC_UNICAST: handle_async_unicast_websocket,
            StreamCommunicationType.SYNC_UNICAST: handle_sync_unicast_websocket,
            StreamCommunicationType.MULTICAST: handle_websocket,
            StreamCommunicationType.BROADCAST: handle_websocket,
        }
        websocket_function = handle_websocket_functions[task_function.communication_type]
        
        async def websocket_endpoint(websocket: WebSocket):
            await websocket_function(websocket)
        
        async def auth_websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
            # response channel must be unique for each websocket
            token_data = verify_token(token)
            user_id = token_data.sub
            await websocket_function(websocket, user_id)

        if task_function.auth:
            end_point = auth_websocket_endpoint
        else:
            end_point = websocket_endpoint
            
        self.router.websocket(
            f"/{to_snake_case(service_name)}/{task_function.name}"
        )(end_point)


def get_app() -> ArbiterApiApp:
    from arbiter.cli import CONFIG_FILE
    from arbiter.cli.utils import read_config
    config = read_config(CONFIG_FILE)
    return ArbiterApiApp(config)

