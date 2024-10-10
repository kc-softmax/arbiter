from __future__ import annotations
import json
import io
import uuid
import asyncio
from pydantic import create_model, BaseModel
from typing import Type, Any
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from arbiter.gateway.exceptions import BadRequest
from arbiter import Arbiter
from arbiter.utils import (
    to_snake_case,
    restore_type,
)
from arbiter.exceptions import TaskBaseError

class ArbiterApiApp(FastAPI):

    def __init__(
        self,
        arbiter: Arbiter,
        lifespan: Any,
        options: dict[str, Any] = {},
    ) -> None:
        super().__init__(lifespan=lifespan)
        self.arbiter = arbiter
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
            **options,
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


        parameters: dict = json.loads(task_function.transformed_parameters)
        parameters = {
            k: (restore_type(v), ...)
            for k, v in parameters.items()
        }
        requset_model = create_model(task_function.name, **parameters)
        return_type = restore_type(json.loads(task_function.transformed_return_type))

        # find base model in parameters
        is_post = True
        for _, v in parameters.items():
            if not issubclass(v[0], BaseModel):
                is_post = False

        async def dynamic_function(
            request: Request,
            data: Type[BaseModel] = Depends(requset_model),  # 동적으로 생성된 Pydantic 모델 사용 # type: ignore
            app: ArbiterApiApp = Depends(get_app),
            task_function: ArbiterTaskModel = Depends(get_task_function),
        ):
            async def stream_response(
                data: BaseModel,
                app: ArbiterApiApp,
                task_function: ArbiterTaskModel,
            ):
                async def stream_response_generator(data_dict: dict[str, Any]):
                    try:
                        async for results in app.arbiter.async_stream_task(
                            target=task_function.queue,
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
            if task_function.request:
                request_data = {
                    'client': request.client,
                    'headers': request.headers,
                    'cookies': request.cookies,
                    'query_params': request.query_params,
                    'path_params': request.path_params,
                }
                data_dict.update({'request': request_data})
            
            if task_function.stream:
                return await stream_response(data_dict, app, task_function)

            try:
                results = await app.arbiter.async_task(
                    target=task_function.queue,
                    **data_dict)
                # TODO 어디에서 에러가 생기든, results 받아온다.
                if isinstance(results, Exception):
                    raise results
                
                # TODO temp, 추후 수정 필요
                if task_function.file:
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

        # TODO MARK : GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD, TRACE, CONNECT
        if is_post:
            self.router.post(
                path,
                tags=[service_name],
                response_model=return_type
            )(dynamic_function)
        else:
            self.router.get(
                path,
                tags=[service_name],
                response_model=return_type
            )(dynamic_function)