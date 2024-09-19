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
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.websockets import WebSocketState
from arbiter.gateway.exceptions import BadRequest
from arbiter import Arbiter
from arbiter.utils import (
    to_snake_case,
    restore_type,
)
from arbiter.data.models import (
    ArbiterTaskModel,
    ArbiterGatewayModel
)
from arbiter.data.messages import ArbiterStreamMessage
from arbiter.gateway.constants import SubscribeChannel
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
        # self.arbiter_server_model: ArbiterGatewayModel = None
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
            async def stream_response(
                data: BaseModel,
                app: ArbiterApiApp,
                task_function: ArbiterTaskModel,
            ):
                async def stream_response_generator(data: BaseModel):
                    try:
                        async for results in app.arbiter.async_stream_task(
                            target=task_function.queue,
                            **data.model_dump()
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
            
            if task_function.stream:
                return await stream_response(data, app, task_function)
            
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
