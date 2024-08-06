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
from typing import Optional, Union, get_args, Type, Any
from fastapi import FastAPI, Query, WebSocket, Depends, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from arbiter.api.exceptions import BadRequest
from arbiter import Arbiter
from arbiter.constants.enums import ArbiterMessageType
from arbiter.utils import (
    to_snake_case,
    create_model_from_schema,
    get_type_from_type_name
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
    ArbiterMessage,
    ARBITER_API_CHANNEL,
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
        self.arbiter: Arbiter = Arbiter(name=name)
        self.stream_routes: dict[str, dict[str, StreamTaskFunction]] = {}
    
    @asynccontextmanager
    async def lifespan(self, app: ArbiterApiApp):
        await self.arbiter.connect()
        self.router_task = asyncio.create_task(self.router_handler())
        await self.arbiter.send_message(
            self.node_id,
            ArbiterMessage(
                data=ArbiterMessageType.API_REGISTER,
                sender_id=self.app_id,
                response=False
            ))
        yield
        self.router_task and self.router_task.cancel()
        await self.arbiter.disconnect()

    async def router_handler(self):
        # message 는 어떤 router로 등록해야 하는가?에 따른다?
        # TODO ADD router, remove Router?
        async for message in self.arbiter.subscribe(ARBITER_API_CHANNEL):
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
        except Exception as e:
            print(e, 'err')
            
        async def dynamic_function(
            data: Type[BaseModel] = Depends(DynamicRequestModel),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            app: ArbiterApiApp = Depends(get_app),
            task_function: HttpTaskFunction = Depends(get_task_function),
        ) -> Union[dict, list[dict], None]:
            try:
                response_required = True if DynamicResponseModel else False
                response = await app.arbiter.send_message(
                    task_function.task_queue,
                    ArbiterMessage(
                        data=data.model_dump_json(),
                        response=response_required))
                # 검사해야 한다.
                if DynamicResponseModel and DynamicResponseModel != Any:
                    # 검사를 해야한다 두 타입이 일치 하는지
                    if type(DynamicResponseModel) != type(response):
                        raise HTTPException(status_code=400, detail=f"Response type is not valid")                    
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
            async def async_websocket_function(
                websocket: WebSocket,
                query: str = None
            ):
                pubsub_id = None
                async def message_listen_queue(websocket: WebSocket, queue: str, time_out: int = 10):
                    # print(f"Start of message_listen_queue {queue}")
                    try:
                        async for data in self.arbiter.listen_bytes(queue, time_out):
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
                        async for data in self.arbiter.subscribe(channel, managed=True):
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
                            if channel:= stream_message.channel:
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
                                            subscribe_tasks[new_subscribe_channel] = asyncio.create_task(
                                                message_subscribe_channel(websocket, new_subscribe_channel.get_channel()))
                                            destination = new_subscribe_channel.get_channel()
                                            
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
                    await self.arbiter.punsubscribe(pubsub_id)
                    pass
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
    arbiter_name = os.getenv("ARBITER_NAME", "Danimoth")
    node_id = os.getenv("NODE_ID", "")
    assert node_id, "NODE_ID is not set"
    
    return ArbiterApiApp(arbiter_name, node_id, config)
