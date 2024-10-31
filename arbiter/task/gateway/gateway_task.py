from __future__ import annotations
import io
import json
import uuid
from fastapi.responses import StreamingResponse
import uvicorn
import asyncio

from typing import Any, Type
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, create_model
from arbiter.exceptions import TaskBaseError
from arbiter.registry.gateway import get_gateway
from multiprocessing.synchronize import Event as MPEvent
from arbiter.configs import ArbiterConfig
from arbiter.data.models import ArbiterTaskNode
from arbiter import Arbiter
from arbiter.utils import restore_type

class ArbiterGateway:
    
    def run(
        self,
        event: MPEvent,
        arbiter_config: ArbiterConfig,
        task_node: list[ArbiterTaskNode],
        *args,
        **kwargs
    ):
        try:
            asyncio.run(
                self._executor(
                    event,
                    arbiter_config,
                    task_node,
                    *args,
                    **kwargs
                )
            )
        except Exception as e:
            print("Error in run", e, self.__class__.__name__)

    async def _executor(
        self,
        event: MPEvent,
        arbiter_config: ArbiterConfig,
        task_node: list[ArbiterTaskNode],
        *args,
        **kwargs
    ):
        try:
            self.arbiter = Arbiter(arbiter_config)
            await self.arbiter.connect()
            gateway = get_gateway(self.arbiter.arbiter_config.name)
            for node in task_node:
                if node.http:
                    self.add_http_task_to_gateway(gateway.app, node)
            server = uvicorn.Server(gateway)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, server.run)
            print("Gateway is running")
            event.wait()
            server.should_exit = True
            # await server.shutdown()
            print("Gateway is closing")
        except Exception as e:
            print("Error in executor", e, self.__class__.__name__)
        finally:
            await self.arbiter.disconnect()

    def add_http_task_to_gateway(
        self,
        fastapi_app: FastAPI,
        task_node: ArbiterTaskNode
    ):
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
                                timeout=task_node.timeout,
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
                        timeout=task_node.timeout,
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
                fastapi_app.router.post(
                    path,
                    response_model=return_type
                )(arbiter_task)
            else:
                fastapi_app.router.get(
                    path,
                    response_model=return_type
                )(arbiter_task)