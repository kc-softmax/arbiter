from __future__ import annotations
import importlib
import json
import uuid
import asyncio
import pickle
import base64
from datetime import datetime
from pydantic import create_model, BaseModel
from configparser import ConfigParser
from fastapi.routing import APIRoute
from uvicorn.workers import UvicornWorker
from typing import Optional, Union, get_args, Type
from fastapi import FastAPI, Query, WebSocket, Depends, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from arbiter.api.auth.router import router as auth_router
from arbiter.api.exceptions import BadRequest
from arbiter.api.auth.dependencies import get_user
from arbiter.broker import RedisBroker, MessageBrokerInterface
from arbiter.constants.enums import ArbiterMessageType
from arbiter.api.auth.utils import verify_token
from arbiter.utils import to_snake_case
from arbiter.database import (
    User,
    Database,
    Node,
    TaskFunction
)
from arbiter.constants.messages import ArbiterStreamMessage
from arbiter.constants.enums import (
    HttpMethod,
    ServiceState,
    StreamCommand,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.constants import (
    ArbiterMessage,
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
    
    async def on_startup(self):
        await self.db.connect()
        await self.broker.connect()
        self.router_task = asyncio.create_task(self.router_handler())
        master_nodes = await self.db.search_data(Node, is_master=True, state=ServiceState.ACTIVE)
        assert len(master_nodes) == 1, "There must be only one master node"
        
        # TODO FIX get master node
        # DB를 Arbiter 이름으로 생성하면 하나밖에 검색이 안된다.
        await self.broker.send_message(
            master_nodes[0].unique_id,
            ArbiterMessage(
                data=ArbiterMessageType.API_REGISTER,
                sender_id=self.app_id
            ))

    async def on_shutdown(self):
        self.router_task and self.router_task.cancel()
        await self.db.disconnect()
        await self.broker.disconnect()

    async def router_handler(self):
        # message 는 어떤 router로 등록해야 하는가?에 따른다?
        # TODO ADD router, remove Router?
        async for message in self.broker.subscribe(ARBITER_API_CHANNEL):
            task_function = TaskFunction.model_validate_json(message)
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
        task_function: TaskFunction,
    ):
        def create_model_from_schema(schema: dict) -> BaseModel:
            type_mapping = {
                'string': str,
                'integer': int,
                'number': float,
                'boolean': bool,
                'datetime': datetime
            }
            fields = {}
            for name, details in schema['properties'].items():
                # datetime 형식의 문자열을 인식하여 datetime 타입으로 변환
                if details.get('format') == 'date-time':
                    field_type = datetime
                else:
                    field_type = type_mapping.get(details['type'], str)  # 기본 타입을 str로 설정
                fields[name] = (field_type, ...)
            return create_model(schema['title'], **fields)     

        def get_task_function() -> TaskFunction:
            return task_function
        def get_app() -> ArbiterApiApp:
            return self
        

        DynamicRequestModel = None
        DynamicResponseModel = None
        list_response = False
        list_request = False
        
        if task_function.response_model:
            response_model = json.loads(task_function.response_model)
            list_response = isinstance(response_model, list)
            if list_response:
                response_model = response_model[0]
            if isinstance(response_model, dict):
                DynamicResponseModel = create_model_from_schema(response_model)
            else:
                DynamicResponseModel = response_model
                
        if task_function.request_models != '[]':
            dynamic_request_params = {}
            request_models = json.loads(task_function.request_models)
            for name, annotation in request_models:
                request_model = None
                list_request = isinstance(annotation, list)
                if list_request:
                    annotation = annotation[0]
                if isinstance(annotation, dict):
                    request_model = create_model_from_schema(annotation)
                else:
                    request_model = annotation
                if list_request:
                    request_model = list[request_model]
                dynamic_request_params[name] = (request_model, ...)
            DynamicRequestModel = create_model(task_function.name + "Model", **dynamic_request_params)
        try:
            if list_response:
                DynamicResponseModel = list[DynamicResponseModel]
        except Exception as e:
            print(e, 'err')
            
        async def process_response(
            response: Union[str, list[str], None], 
            response_model_type: Optional[type[BaseModel]]) -> Union[dict, list[dict], None]:
            if not response:
                raise Exception("Failed to get response")
            # response 가 다른 타입일수 있을까? int, etc,
            response = json.loads(response) if isinstance(response, str) else response
            if not response_model_type:
                return response
            if isinstance(response, list):
                assert issubclass(response_model_type, BaseModel), "Response model must be subclass of Pydantic BaseModel"
                return [response_model_type.model_validate_json(res) for res in response]
            return response_model_type.model_validate(response)

        async def dynamic_function_no_request(
            app: ArbiterApiApp = Depends(get_app),
            task_function: TaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            response_required = True if DynamicResponseModel else False
            response = await app.broker.send_message(
                task_function.queue_name,
                ArbiterMessage(
                    sender_id=self.app_id,
                    response=response_required))
            if not DynamicResponseModel:
                return response
            if list_response:
                response_model_type = get_args(DynamicResponseModel)[0]
            else:
                response_model_type = DynamicResponseModel
            return await process_response(response, response_model_type)

        async def dynamic_auth_function_no_request(
            user: User = Depends(get_user),
            app: ArbiterApiApp = Depends(get_app),
            task_function: TaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            response_required = True if DynamicResponseModel else False
            response = await app.broker.send_message(
                task_function.queue_name,
                ArbiterMessage(
                    data=json.dumps(dict(user_id=user.id)),
                    sender_id=self.app_id,
                    response=response_required))
            if not DynamicResponseModel:
                return response
            if list_response:
                response_model_type = get_args(DynamicResponseModel)[0]
            else:
                response_model_type = DynamicResponseModel
            return await process_response(response, response_model_type)

        async def dynamic_function(
            data: Type[BaseModel] = Depends(DynamicRequestModel),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            app: ArbiterApiApp = Depends(get_app),
            task_function: TaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            response_required = True if DynamicResponseModel else False
            response = await app.broker.send_message(
                task_function.queue_name,
                ArbiterMessage(
                    data=data.model_dump_json(), 
                    sender_id=self.app_id,
                    response=response_required))                    
            if not DynamicResponseModel:
                return response
            if list_response:
                response_model_type = get_args(DynamicResponseModel)[0]
            else:
                response_model_type = DynamicResponseModel
            return await process_response(response, response_model_type)
        
        async def dynamic_auth_function(
            data: Type[BaseModel] = Depends(DynamicRequestModel),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            user: User = Depends(get_user),
            app: ArbiterApiApp = Depends(get_app),
            task_function: TaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            data_dict = data.model_dump()
            data_dict["user_id"] = user.id
            response_required = True if DynamicResponseModel else False
            response = await app.broker.send_message(
                task_function.queue_name,
                ArbiterMessage(
                    data=json.dumps(data_dict),
                    sender_id=self.app_id,
                    response=response_required))                    
            if not DynamicResponseModel:
                return response
            if list_response:
                response_model_type = get_args(DynamicResponseModel)[0]
            else:
                response_model_type = DynamicResponseModel
            return await process_response(response, response_model_type)


        if task_function.auth:
            end_point = dynamic_auth_function if DynamicRequestModel else dynamic_auth_function_no_request
        else:
            end_point = dynamic_function if DynamicRequestModel else dynamic_function_no_request
            if DynamicResponseModel:
                self.router.post(
                    f'/{to_snake_case(service_name)}/{task_function.name}',
                    tags=[service_name],
                    response_model=DynamicResponseModel
                )(end_point)
            else:
                self.router.post(
                    f'/{to_snake_case(service_name)}/{task_function.name}',
                    tags=[service_name]
                )(end_point)
                    
    def generate_websocket_function(
            self,
            service_name: str,
            task_function: TaskFunction,
        ):        
            async def message_listen_queue(websocket: WebSocket, queue: str, time_out: int = 10):
                async for data in self.broker.listen_bytes(queue, time_out):
                    if data is None:
                        data = {"from": queue, "data": 'LEAVE'}
                        await websocket.send_text(json.dumps(data))
                        break
                    data = {"from": queue, "data": data.decode()}
                    await websocket.send_text(json.dumps(data))

            async def message_subscribe_channel(websocket: WebSocket, channel: str):
                async for data in self.broker.subscribe(channel):
                    data = {"from": channel, "data": data}
                    await websocket.send_text(json.dumps(data))
                    
            async def async_websocket_function(
                websocket: WebSocket,
                user_id: str = None
            ):
                await websocket.accept()
                
                response_queue = uuid.uuid4().hex
                if user_id:
                    if user:= await self.db.get_data(User, user_id):
                        response_queue = user.unique_channel
                # stream communication type 수에 따라서 response_queue를 생성한다.                
                # response task가 만들어질때, response_queue를 인자로 넘겨준다.
                message_tasks: dict[str, asyncio.Task] = {}
                message_tasks[response_queue] = asyncio.create_task(message_listen_queue(websocket, response_queue))
                try:
                    target = None
                    while True:
                        receive_data = await websocket.receive_text()
                        if not receive_data: 
                            continue
                        # target은 믿는다.
                        try:
                            json_data = json.loads(receive_data)
                            
                            to_remove_tasks = [
                                key for key, value in message_tasks.items() if value.done()
                            ]
                            for key in to_remove_tasks:
                                message_tasks.pop(key)
                                
                            stream_message = ArbiterStreamMessage.model_validate_json(json_data)
                                                            
                            match stream_message.command:
                                case StreamCommand.UNSUBSCRIBE:
                                    channel = stream_message.data
                                    if not channel:
                                        continue
                                    if channel not in message_tasks:
                                        await websocket.send_text(f"Already unsubscribed to {channel}")
                                        continue
                                    if not message_tasks[channel].done():
                                        message_tasks[channel].cancel()
                                case StreamCommand.SUBSCRIBE:
                                    channel = stream_message.data
                                    if not channel:
                                        continue
                                    if channel in message_tasks and not message_tasks[channel].done():
                                        await websocket.send_text(f"Already subscribed to {channel}")
                                        continue
                                    message_tasks[channel] = asyncio.create_task(message_subscribe_channel(websocket, channel))
                                    target = channel
                                case StreamCommand.SET_TARGET:
                                    new_target = stream_message.data
                                    # target validation
                                    target = new_target
                        except json.JSONDecodeError:
                            # receive_data should be bytes and str
                            assert isinstance(receive_data, (bytes, str)), "Data must be bytes or str"
                            
                            # target 종류에 따라서 다른 처리방법을 사용해야 한다.
                            # target이 broadcast인 경우, response_queue는 없어도 된다.
                            await self.broker.push_message(
                                task_function.queue_name,
                                pickle.dumps(
                                    (
                                        None if target in message_tasks else response_queue,
                                        target, 
                                        receive_data)
                                )
                            )
                except WebSocketDisconnect:
                    pass
                results = await asyncio.gather(*message_tasks.values(), return_exceptions=True)
                if not websocket.client_state == WebSocketState.DISCONNECTED:
                    await websocket.close()

            async def sync_websocket_function(
                websocket: WebSocket,
                user_id: str = None
            ):
                await websocket.accept()
                try:
                    response_queue = uuid.uuid4().hex
                    try:
                        if user_id:
                            if user:= await self.db.get_data(User, user_id):
                                response_queue = user.unique_channel
                    except Exception as e:
                        print(e, 'err - code ws-1')
                        
                    target = None
                    while True:
                        # target은 믿는다.
                        try:
                            receive_data = await websocket.receive_text()
                            json_data = json.loads(receive_data)
                            
                            stream_message = ArbiterStreamMessage.model_validate_json(json_data)
                                                            
                            match stream_message.command:
                                case StreamCommand.SET_TARGET:
                                    new_target = stream_message.data
                                    # target validation
                                    if new_target:
                                        target = new_target
                        except json.JSONDecodeError:
                            # receive_data should be bytes and str
                            assert isinstance(receive_data, (bytes, str)), "Data must be bytes or str"
                            
                            await self.broker.push_message(
                                task_function.queue_name,
                                pickle.dumps((response_queue, target, receive_data))
                            )
                            try:
                                message = await self.broker.get_message(response_queue)
                            except TimeoutError:
                                
                                break
                            await websocket.send_text(message.decode())
                except WebSocketDisconnect:
                    pass
                if not websocket.client_state == WebSocketState.DISCONNECTED:
                    await websocket.close()

            async def websocket_endpoint(websocket: WebSocket):
                match task_function.communication_type:
                    case StreamCommunicationType.SYNC:
                        await sync_websocket_function(websocket)
                    case StreamCommunicationType.ASYNC:
                        await async_websocket_function(websocket)
            
            async def auth_websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
                # response channel must be unique for each websocket
                token_data = verify_token(token)
                user_id = token_data.sub
                match task_function.communication_type:
                    case StreamCommunicationType.SYNC:
                        await sync_websocket_function(websocket, user_id)
                    case StreamCommunicationType.ASYNC:
                        await async_websocket_function(websocket, user_id)

            if task_function.auth:
                end_point = auth_websocket_endpoint
            else:
                end_point = websocket_endpoint
            self.router.websocket(
                f"/{to_snake_case(service_name)}/{task_function.name}",
            )(end_point)


def get_app() -> ArbiterApiApp:
    
    from arbiter.cli import CONFIG_FILE
    from arbiter.cli.utils import read_config
    config = read_config(CONFIG_FILE)
    return ArbiterApiApp(config)

