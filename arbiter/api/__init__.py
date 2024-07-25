from __future__ import annotations
import os
import json
import uuid
import asyncio
import pickle
from contextlib import asynccontextmanager
from datetime import datetime
from pydantic import create_model, BaseModel, ValidationError
from configparser import ConfigParser
from uvicorn.workers import UvicornWorker
from typing import Optional, Union, get_args, Type
from fastapi import FastAPI, Query, WebSocket, Depends, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from arbiter.api.exceptions import BadRequest
from arbiter.broker import RedisBroker
from arbiter.constants.enums import ArbiterMessageType
from arbiter.utils import to_snake_case
from arbiter.database.model import (
    Node,
    HttpTaskFunction,
    StreamTaskFunction
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


class NetworkChannel:
    
    def __init__(self, channel: str, target: int | str = None):
        self.channel = channel
        self.target = target
        
    def get_channel(self):
        if self.target:
            return f"{self.channel}_{self.target}"
        return self.channel


class ArbiterApiApp(FastAPI):

    def __init__(
        self,
        name: str,
        node_id: str,
        config: ConfigParser,
    ) -> None:
        super().__init__(lifespan=self.lifespan)
        self.name = name
        self.node_id = node_id
        self.app_id = uuid.uuid4().hex
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
        self.router_task: asyncio.Task = None
        self.broker: RedisBroker = RedisBroker(name=name)
        self.stream_routes: dict[str, dict[str, StreamTaskFunction]] = {}
    
    @asynccontextmanager
    async def lifespan(self, app: ArbiterApiApp):
        await self.broker.connect()
        self.router_task = asyncio.create_task(self.router_handler())
        await self.broker.send_message(
            self.node_id,
            ArbiterMessage(
                data=ArbiterMessageType.API_REGISTER,
                sender_id=self.app_id,
                response=False
            ))
        yield
        self.router_task and self.router_task.cancel()
        await self.broker.disconnect()

    async def router_handler(self):
        # message 는 어떤 router로 등록해야 하는가?에 따른다?
        # TODO ADD router, remove Router?
        async for message in self.broker.subscribe(ARBITER_API_CHANNEL):
            try:
                http_task_function = HttpTaskFunction.model_validate_json(message)
                service_name = http_task_function.service_meta.name
            except Exception as e: # TODO Exception type more detail
                print(e)
            try:
                stream_task_function = StreamTaskFunction.model_validate_json(message)
                service_name = stream_task_function.service_meta.name
            except Exception as e: # TODO Exception type more detail
                print(e)
            
            assert http_task_function or stream_task_function, "Task function is not valid"   
            
            
            # 이미 라우터에 등록되어 있다면 무시한다.
            # already_registered = False
            # for route in self.routes:
            #     route: APIRoute
            #     path = f"/{to_snake_case(service_name)}/{task_function.name}"
            #     if route.path == path:
            #         already_registered = True
                # print(path)
                # print(route.path, route.methods)
                # # if path in router.pat:
                #     # continue
            # if already_registered:
            #     continue
            if http_task_function:
                match http_task_function.method:
                    case HttpMethod.POST:
                        self.generate_post_function(
                            service_name,
                            http_task_function
                        )
            if stream_task_function:
                match stream_task_function.connection:
                    case StreamMethod.WEBSOCKET:
                        self.generate_websocket_function(
                            service_name,
                            stream_task_function)

            self.openapi_schema = None

    def generate_post_function(
        self,
        service_name: str,
        task_function: HttpTaskFunction,
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

        def get_task_function() -> HttpTaskFunction:
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
            response_model_type: Optional[type[BaseModel]]) -> Union[BaseModel, None]:
            if not response:
                return 'timeout'
                # todo error handling
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
            task_function: HttpTaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            try:
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
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to get response {e}")


        async def dynamic_function(
            data: Type[BaseModel] = Depends(DynamicRequestModel),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            app: ArbiterApiApp = Depends(get_app),
            task_function: HttpTaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            try:
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
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to get response {e}")

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
            task_function: StreamTaskFunction,
        ):
            async def async_websocket_function(
                websocket: WebSocket,
                query: str = None
            ):
                pubsub_id = None
                async def message_listen_queue(websocket: WebSocket, queue: str, time_out: int = 10):
                    # print(f"Start of message_listen_queue {queue}")
                    try:
                        async for data in self.broker.listen_bytes(queue, time_out):
                            if data is None:
                                data = {"from": queue, "data": 'LEAVE'}
                                await websocket.send_text(json.dumps(data))
                                break
                            data = {"from": queue, "data": data.decode()}
                            await websocket.send_text(json.dumps(data))
                    except asyncio.CancelledError:
                        pass
                        # print(f"listen to {queue} cancelled")
                    # finally:
                        # print(f"End of message_listen_queue {queue}")
                        

                async def message_subscribe_channel(websocket: WebSocket, channel: str):
                    # print(f"Start of message_subscribe_channel {channel}")
                    try:
                        nonlocal pubsub_id
                        async for data in self.broker.subscribe(channel, managed=True):
                            if not pubsub_id:
                                pubsub_id = data
                            else:
                                data = {"from": channel, "data": data.decode()}
                                await websocket.send_text(json.dumps(data))
                    except asyncio.CancelledError:
                        pass
                        # print(f"Subscription to {channel} cancelled")
                    # finally:
                        # print(f"End of message_subscribe_channel {channel}")
                
                stream_route = self.stream_routes[service_name]
                #broker 할당 받은 받기
                # 할당 못받으면 GG
                
                await websocket.accept()

                response_queue = uuid.uuid4().hex                          
                # response task가 만들어질때, response_queue를 인자로 넘겨준다.
                message_tasks: dict[NetworkChannel, asyncio.Task] = {}
                response_task = asyncio.create_task(message_listen_queue(websocket, response_queue, 0))
                try:
                    destination: str | None = None
                    target_task_function: StreamTaskFunction | None = None
                    while True:
                        receive_data = await websocket.receive_text()
                        if not receive_data: 
                            continue
                        try:                            
                            json_data = json.loads(receive_data)
                            
                            to_remove_tasks = [
                                key for key, value in message_tasks.items() if value.done()
                            ]
                            for key in to_remove_tasks:
                                message_tasks.pop(key)
                            stream_message = ArbiterStreamMessage.model_validate(json_data)
                            if stream_message.channel:
                                network_channel = NetworkChannel(stream_message.channel, stream_message.target)
                                # get StreamTaskFunction from channel
                                task_function = stream_route.get(network_channel.channel)
                                if not task_function:
                                    await websocket.send_text(f"Channel {network_channel.channel} is not valid")
                                    await websocket.send_text(f"Valid channels are {list(stream_route.keys())}")
                                    continue
                                match task_function.communication_type:
                                    case StreamCommunicationType.SYNC_UNICAST:
                                        if network_channel.target:
                                            destination = network_channel.target
                                        else:
                                            destination = response_queue
                                    case StreamCommunicationType.ASYNC_UNICAST:
                                        if network_channel.target:
                                            destination = network_channel.target
                                        else:
                                            destination = response_queue
                                    case StreamCommunicationType.BROADCAST:
                                        # validate target
                                        if target:= network_channel.target:
                                            try:
                                                target = int(target)
                                            except ValueError:
                                                await websocket.send_text(f"in broadcast type, Target must be integer")
                                                continue
                                            if target > task_function.num_of_channels:
                                                await websocket.send_text(f"Target must be less than {task_function.num_of_channels}")
                                                continue
                                        to_subscribe_task = True
                                        for message_channel in message_tasks:
                                            if message_channel.channel != network_channel.channel:
                                                continue
                                            if message_channel.get_channel() == network_channel.get_channel():
                                                # await websocket.send_text(f"Already subscribed to {network_channel.get_channel()}")
                                                to_subscribe_task = False
                                                break
                                            message_tasks[message_channel].cancel()
                                            await message_tasks[message_channel]
                                        if to_subscribe_task:
                                            message_tasks[network_channel] = asyncio.create_task(
                                                message_subscribe_channel(websocket, network_channel.get_channel()))
                                            destination = network_channel.get_channel()
                                target_task_function = task_function
                                if not stream_message.message:
                                    await websocket.send_text('OK')
                            if stream_message.message:
                                if not isinstance(stream_message.message, (bytes, str)):
                                    await websocket.send_text(f"message must be bytes or str")
                                    continue
                                if not target_task_function or not destination:
                                    # server error 확률 높
                                    await websocket.send_text(f"Target is not set")
                                    continue
                                    # data
                                await self.broker.push_message(
                                    target_task_function.queue_name,
                                    pickle.dumps(
                                        (
                                            destination, 
                                            stream_message.message,
                                            stream_message.info
                                        )
                                    ))
                            
                        # excepe pydantic_core._pydantic_core.ValidationError as e:
                        except ValidationError as e:
                            await websocket.send_text(f"Data is not valid {e}")
                        except json.JSONDecodeError:
                            await websocket.send_text(f"Data is not valid json")
                except WebSocketDisconnect:
                    await self.broker.punsubscribe(pubsub_id)
                    pass
                if response_task:
                    response_task.cancel()
                await asyncio.gather(*message_tasks.values(), return_exceptions=True)
                if not websocket.client_state == WebSocketState.DISCONNECTED:
                    await websocket.close()
            
            async def websocket_endpoint(websocket: WebSocket, query: str = Query(None)):
                # response channel must be unique for each websocket
                await async_websocket_function(websocket, query)

            if service_name not in self.stream_routes:
                self.stream_routes[service_name] = {}            
                self.router.websocket(
                    f"/stream/{to_snake_case(service_name)}",
                )(websocket_endpoint)

            self.stream_routes[service_name][task_function.name] = task_function


def get_app() -> ArbiterApiApp:
    
    from arbiter.cli import CONFIG_FILE
    from arbiter.cli.utils import read_config
    config = read_config(CONFIG_FILE)
    arbiter_name = os.getenv("ARBITER_NAME", "Danimoth")
    node_id = os.getenv("NODE_ID", "")
    assert node_id, "NODE_ID is not set"
    
    return ArbiterApiApp(arbiter_name, node_id, config)
