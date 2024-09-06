from __future__ import annotations
import json
import uuid
import asyncio
import pickle
from pydantic import create_model, BaseModel, ValidationError
from typing import Union, Type, Any, Optional, get_args
from fastapi import FastAPI, Query, WebSocket, Depends, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from arbiter.server.exceptions import BadRequest
from arbiter import Arbiter
from arbiter.utils import (
    is_optional_type,
    to_snake_case,
    get_pickled_data,
    restore_type,
)
from arbiter.data.models import (
    ArbiterTaskModel,
    ArbiterServerModel
)
from arbiter.data.messages import ArbiterStreamMessage
from arbiter.enums import (
    HttpMethod,
    StreamMethod,
    StreamCommunicationType
)
from arbiter.server.constants import SubscribeChannel
from arbiter.exceptions import TaskBaseError

class ArbiterApiApp(FastAPI):

    def __init__(
        self,
        arbiter: Arbiter,
        lifespan: Any,
        allow_origins: str = "*",
        allow_methods: str = "*",
        allow_headers: str = "*",
        allow_credentials: bool = True,
    ) -> None:
        super().__init__(lifespan=lifespan)
        self.arbiter = arbiter
        self.arbiter_server_model: ArbiterServerModel = None
        self.add_exception_handler(
            RequestValidationError,
            lambda request, exc: JSONResponse(
                status_code=BadRequest.STATUS_CODE,
                content={"detail": BadRequest.DETAIL}
            )
        )
        self.add_exception_handler(
            500,
            lambda request, exc: JSONResponse(
                status_code=500,
                content={"detail": str(exc)}
            )
        )
        self.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
        )
        self.stream_routes: dict[str, dict[str, ArbiterTaskModel]] = {} 

    def generate_http_function(
        self,
        task_function: ArbiterTaskModel,
    ):
        def get_task_function() -> ArbiterTaskModel:
            return task_function
        def get_app() -> ArbiterApiApp:
            return self
       
        service_name = task_function.service_name
        path = f'/{to_snake_case(service_name)}/{task_function.name}'

        try:
            parameters: dict = json.loads(task_function.transformed_parameters)
            parameters = {
                k: (restore_type(v), ...)
                for k, v in parameters.items()
            }
            requset_model = create_model(task_function.name, **parameters)
            return_type = restore_type(json.loads(task_function.transformed_return_type))
        except Exception as e:
            print('Error in generate_http_function', e)
        
        async def dynamic_post_function(
            data: Type[BaseModel] = Depends(requset_model),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            app: ArbiterApiApp = Depends(get_app),
            task_function: ArbiterTaskModel = Depends(get_task_function),
        ):
            try:
                results = await app.arbiter.async_task(
                    target=task_function.queue,
                    **data.model_dump())
                                
                if isinstance(results, Exception):
                    raise results
                return results
            except TaskBaseError as e:
                raise e
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to get response {e}")

        # TODO MARK : GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD, TRACE, CONNECT
        self.router.post(
            path,
            tags=[service_name],
            response_model=return_type
        )(dynamic_post_function)

    def generate_stream_function(
            self,
            task_function: ArbiterTaskModel,
        ):
            # currently not using DynamicRequestModel, DynamicResponseModel
            # TODO if need to check request or response model validation, use it
            # DynamicRequestModel, DynamicResponseModel = self.get_dynamic_models(task_function)
            service_name = task_function.service_name
            async def async_websocket_function(
                websocket: WebSocket,
                query: str = None
            ):
                # 웹소켓 연결시 고유의 pubsub_id_prefix와 pubsub_id를 관리하여 이후에 unsub하는 리스트를 생성
                pubsub_id_prefix = uuid.uuid4().hex
                pubsub_channels: list[str] = []

                async def message_listen_queue(websocket: WebSocket, queue: str, timeout: int = 10):
                    try:
                        async for data in self.arbiter.listen(queue, timeout):
                            if data is None:
                                data = {"from": queue, "data": 'Timeout'}
                                await websocket.send_text(json.dumps(data))
                                break
                            data = get_pickled_data(data)
                            data = {"from": queue, "data": data}
                            await websocket.send_text(json.dumps(data))
                    except asyncio.CancelledError:
                        pass

                async def message_subscribe_channel(websocket: WebSocket, channel: str, pubsub_id: str):
                    try:
                        async for data in self.arbiter.subscribe_listen(channel, pubsub_id):
                            data = get_pickled_data(data)
                            if isinstance(data, BaseModel):
                                data = data.model_dump()
                            data = {"from": channel, "data": data}
                            await websocket.send_text(json.dumps(data))
                    except asyncio.CancelledError as e:
                        print(e)
                        pass
                    except Exception as e:
                        print(e)
                
                stream_route = self.stream_routes[service_name]
                # query에 관한 처리가 있어야 한다.
                # service의 handle query 같은것이 필요하다.

                await websocket.accept()
                response_task: asyncio.Task = None
                response_queue = uuid.uuid4().hex                          
                # response task가 만들어질때, response_queue를 인자로 넘겨준다.
                subscribe_tasks: dict[SubscribeChannel, asyncio.Task] = {}
                try:
                    destination: str | None = None
                    target_task_function: ArbiterTaskModel | None = None
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
                                            await asyncio.sleep(0.1)

                                target_task_function = task_function
                                if not stream_message.data:
                                    await websocket.send_text('OK')
                            if stream_message.data:
                                if not target_task_function or not destination:
                                    # server error 확률 높
                                    await websocket.send_text(f"Target is not set")
                                    continue
                                    # data
                                if not response_task or response_task.done():
                                    response_task = asyncio.create_task(
                                        message_listen_queue(websocket, response_queue, 0))
                                data = stream_message.data
                                if not isinstance(data, dict):
                                    data = [data]
                                data = pickle.dumps((destination, data))
                                await self.arbiter.push_message(
                                    target_task_function.queue,
                                    data)

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
            
