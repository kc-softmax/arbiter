from __future__ import annotations
import os
import json
import uuid
import asyncio
import pickle
from contextlib import asynccontextmanager
from pydantic import create_model, BaseModel, ValidationError
from configparser import ConfigParser
from uvicorn.workers import UvicornWorker
from typing import Union, Type, Any
from fastapi import FastAPI, Query, WebSocket, Depends, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from arbiter.api.exceptions import BadRequest
from arbiter import Arbiter
from arbiter.utils import (
    to_snake_case,
    create_model_from_schema,
    get_type_from_type_name, 
    get_pickled_data
)
from arbiter.database.model import (
    HttpTaskFunction,
    StreamTaskFunction
)
from arbiter.constants.messages import ArbiterStreamMessage
from arbiter.constants.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.constants import (
    ArbiterDataType,
    ArbiterTypedData,
)


ArbiterUvicornWorker = UvicornWorker
ArbiterUvicornWorker.CONFIG_KWARGS = {"loop": "asyncio", "http": "auto"}

class SubscribeChannel:
    
    def __init__(self, channel: str, target: int | str = None):
        self.channel = channel
        self.target = target
        
    def get_channel(self):
        if self.target:
            return f"{self.channel}_{self.target}"
        return self.channel
    
    def __eq__(self, value: SubscribeChannel) -> bool:
        return self.get_channel() == value.get_channel()

    def __hash__(self):
        return self.get_channel().__hash__()


class ArbiterApiApp(FastAPI):

    def __init__(
        self,
        node_id: str,
        config: ConfigParser,
    ) -> None:
        super().__init__(lifespan=self.lifespan)
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
        self.arbiter: Arbiter = Arbiter()
        self.stream_routes: dict[str, dict[str, StreamTaskFunction]] = {}
    
    @asynccontextmanager
    async def lifespan(self, app: ArbiterApiApp):
        await self.arbiter.connect()
        self.router_task = asyncio.create_task(self.router_handler())
        await self.arbiter.send_message(
            receiver_id=self.node_id,
            data=ArbiterTypedData(
                type=ArbiterDataType.API_REGISTER,
                data=self.app_id                
            ).model_dump_json())
        yield
        self.router_task and self.router_task.cancel()
        await self.arbiter.disconnect()

    def get_dynamic_models(
        self,
        task_function: HttpTaskFunction | StreamTaskFunction,
    ):
        DynamicRequestModel = None
        DynamicResponseModel = None
        list_response = False
        list_request = False
        try:
            if task_response := task_function.task_response:
                response_type = json.loads(task_response)
                list_response = isinstance(response_type, list)
                if list_response:
                    response_type = response_type[0]
                if not response_type:
                    DynamicResponseModel = None                    
                elif isinstance(response_type, dict):
                    DynamicResponseModel = create_model_from_schema(response_type)
                else:
                    DynamicResponseModel = get_type_from_type_name(response_type)
                if list_response:
                    DynamicResponseModel = list[DynamicResponseModel]
                    
            if task_params := task_function.task_params:
                dynamic_params = {}
                params: dict[str, str] = json.loads(task_params)
                for name, flat_annotation in params.items():
                    param = None
                    list_param = isinstance(flat_annotation, list)
                    if list_param:
                        param = param[0]                        
                    if isinstance(flat_annotation, dict):
                        param_model = create_model_from_schema(flat_annotation)
                    else:
                        param_model = flat_annotation                        
                    if list_request:
                        param_model = list[param_model]
                    dynamic_params[name] = (param_model, ...)
                DynamicRequestModel = create_model(task_function.name + "Model", **dynamic_params)
            return DynamicRequestModel, DynamicResponseModel
        except Exception as e:
            print('err in get_dynamic_models', e)
            return None, None

    async def router_handler(self):
        # message 는 어떤 router로 등록해야 하는가?에 따른다?
        # TODO ADD router, remove Router?
        async for message in self.arbiter.subscribe_listen(self.node_id + '_router'):
            try:
                http_task_function = HttpTaskFunction.model_validate_json(message)
                service_name = http_task_function.service_meta.name
            except Exception as e: # TODO Exception type more detail
                print(e, 'err')
            try:
                stream_task_function = StreamTaskFunction.model_validate_json(message)
                service_name = stream_task_function.service_meta.name
            except Exception as e: # TODO Exception type more detail
                print(e, 'errr')
            
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
        def get_task_function() -> HttpTaskFunction:
            return task_function
        def get_app() -> ArbiterApiApp:
            return self
        
        path = f'/{to_snake_case(service_name)}/{task_function.name}'
        DynamicRequestModel, DynamicResponseModel = self.get_dynamic_models(task_function)
            
        async def dynamic_function(
            data: Type[BaseModel] = Depends(DynamicRequestModel),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            app: ArbiterApiApp = Depends(get_app),
            task_function: HttpTaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            try:
                response_required = True if DynamicResponseModel else False
                response = await app.arbiter.send_message(
                    receiver_id=task_function.task_queue,
                    data=data.model_dump_json(),
                    wait_response=response_required)
                # 값을 보낼때는 그냥 믿고 보내준다.
                # 타입이 다르다고 하더라도, 그냥 보내준다.
                # if DynamicResponseModel and DynamicResponseModel != Any:
                #     # 검사를 해야한다 두 타입이 일치 하는지
                #     if issubclass(DynamicResponseModel, BaseModel):
                #         response = DynamicResponseModel.model_validate_json(response)
                #     if DynamicResponseModel != type(response):
                #         raise HTTPException(status_code=400, detail=f"Response type is not valid")
                return response
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to get response {e}")

        self.router.post(
            path,
            tags=[service_name],
            response_model=DynamicResponseModel
        )(dynamic_function)

    def generate_websocket_function(
            self,
            service_name: str,
            task_function: StreamTaskFunction,
        ):
            # currently not using DynamicRequestModel, DynamicResponseModel
            # TODO if need to check request or response model validation, use it
            # DynamicRequestModel, DynamicResponseModel = self.get_dynamic_models(task_function)
            async def async_websocket_function(
                websocket: WebSocket,
                query: str = None
            ):
                # 웹소켓 연결시 고유의 pubsub_id_prefix와 pubsub_id를 관리하여 이후에 unsub하는 리스트를 생성
                pubsub_id_prefix = uuid.uuid4().hex
                pubsub_channels: list[str] = []

                async def message_listen_queue(websocket: WebSocket, queue: str, timeout: int = 10):
                    try:
                        async for data in self.arbiter.listen_bytes(queue, timeout):
                            if data is None:
                                data = {"from": queue, "data": 'LEAVE'}
                                await websocket.send_text(json.dumps(data))
                                break
                            data = get_pickled_data(data)
                            if isinstance(data, BaseModel):
                                data = data.model_dump()
                            data = {"from": queue, "data": data}
                            await websocket.send_text(json.dumps(data))
                    except asyncio.CancelledError:
                        pass
                        # print(f"listen to {queue} cancelled")
                    # finally:
                        # print(f"End of message_listen_queue {queue}")
                        
                async def message_subscribe_channel(websocket: WebSocket, channel: str, pubsub_id: str):
                    # print(f"Start of message_subscribe_channel {channel}")
                    try:
                        async for data in self.arbiter.subscribe_listen(channel, pubsub_id):
                            data = get_pickled_data(data)
                            if isinstance(data, BaseModel):
                                data = data.model_dump()
                            data = {"from": channel, "data": data}
                            await websocket.send_text(json.dumps(data))
                    except asyncio.CancelledError:
                        pass
                        # print(f"Subscription to {channel} cancelled")
                    # finally:
                        # print(f"End of message_subscribe_channel {channel}")
                
                stream_route = self.stream_routes[service_name]
                # query에 관한 처리가 있어야 한다.
                # service의 handle query 같은것이 필요하다.
                
                await websocket.accept()

                response_queue = uuid.uuid4().hex                          
                # response task가 만들어질때, response_queue를 인자로 넘겨준다.
                subscribe_tasks: dict[SubscribeChannel, asyncio.Task] = {}
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
                                key for key, value in subscribe_tasks.items() if value.done()
                            ]
                            for key in to_remove_tasks:
                                subscribe_tasks.pop(key)
                            stream_message = ArbiterStreamMessage.model_validate(json_data)
                            if channel := stream_message.channel:
                                # get StreamTaskFunction from channel
                                task_function = stream_route.get(channel)
                                if not task_function:
                                    await websocket.send_text(f"Channel {channel} is not valid")
                                    await websocket.send_text(f"Valid channels are {list(stream_route.keys())}")
                                    continue

                                target = stream_message.target
                                if (
                                    task_function.communication_type != StreamCommunicationType.BROADCAST and
                                    not target
                                ):
                                    # if target is not set, use response_queue
                                    target = response_queue
                                                                    
                                match task_function.communication_type:
                                    case StreamCommunicationType.SYNC_UNICAST:
                                        destination = target
                                    case StreamCommunicationType.ASYNC_UNICAST:
                                        destination = target
                                    case StreamCommunicationType.BROADCAST:
                                        new_subscribe_channel = SubscribeChannel(channel, stream_message.target)
                                        destination = new_subscribe_channel.get_channel()
                                        # validate target
                                        if target:
                                            try:
                                                target = int(target)
                                            except ValueError:
                                                await websocket.send_text(f"in broadcast type, Target must be integer")
                                                continue
                                            if target > task_function.num_of_channels:
                                                await websocket.send_text(f"Target must be less than {task_function.num_of_channels}")
                                                continue
                                        to_subscribe_task = True
                                        for subscribe_channel in subscribe_tasks:
                                            if subscribe_channel.channel != channel:
                                                continue
                                            if subscribe_channel == new_subscribe_channel:
                                                # await websocket.send_text(f"Already subscribed to {network_channel.get_channel()}")
                                                to_subscribe_task = False
                                                break
                                            subscribe_tasks[subscribe_channel].cancel()
                                            await subscribe_tasks[subscribe_channel]

                                        if to_subscribe_task:
                                            # 채널별로 pubsub이 생성 vs 한 개의 pubsub에 여러개의 채널을 구독한다
                                            pubsub_id = f"{pubsub_id_prefix}_{destination}"
                                            pubsub_channels.append(pubsub_id)
                                            subscribe_tasks[new_subscribe_channel] = asyncio.create_task(
                                                message_subscribe_channel(websocket, destination, pubsub_id))

                                target_task_function = task_function
                                if not stream_message.data:
                                    await websocket.send_text('OK')
                                    
                            if stream_message.data:
                                if not target_task_function or not destination:
                                    # server error 확률 높
                                    await websocket.send_text(f"Target is not set")
                                    continue
                                    # data
                                await self.arbiter.push_message(
                                    target_task_function.task_queue,
                                    pickle.dumps(
                                        (
                                            destination, 
                                            stream_message.data
                                        )
                                    ))
                            
                        # excepe pydantic_core._pydantic_core.ValidationError as e:
                        except ValidationError as e:
                            await websocket.send_text(f"Data is not valid {e}")
                        except json.JSONDecodeError:
                            await websocket.send_text(f"Data is not valid json")
                except WebSocketDisconnect:
                    for pubsub_id in pubsub_channels:
                        await self.arbiter.punsubscribe(pubsub_id)

                if response_task:
                    response_task.cancel()
                await asyncio.gather(*subscribe_tasks.values(), return_exceptions=True)
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
    node_id = os.getenv("NODE_ID", "")
    assert node_id, "NODE_ID is not set"
    
    return ArbiterApiApp(node_id, config)
