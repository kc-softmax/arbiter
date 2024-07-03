import asyncio
import pickle
import uuid
import uvicorn
from typing import Optional, Union, Callable
from fastapi import APIRouter, FastAPI, Depends, WebSocket, Query, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from arbiter.api.auth.dependencies import get_user
from arbiter.constants.enums import HttpMethod, StreamMethod
from arbiter.database import (
    Database,
    ServiceMeta,
    TaskFunction,
    User
)
from arbiter.service.redis_service import RedisService
from arbiter.api.auth.router import router as auth_router
from arbiter.api.auth.utils import verify_token
from arbiter.utils import to_snake_case


class ApiService(RedisService):

    def __init__(self, app: FastAPI, server: uvicorn.Server):
        super().__init__()
        self.db = Database.get_db()
        self.app = app
        self.server = server

    @classmethod
    async def launch(
        cls,
        node_id: str,
        service_id: str,
        **kwargs
    ):
        app = FastAPI()
        app.include_router(auth_router)
        app.add_middleware(
            CORSMiddleware,
            allow_origins='*',
            allow_credentials=True,
            allow_methods='*',
            allow_headers='*'
        )
        config = uvicorn.Config(
            app,
            host=kwargs.get('host', '0.0.0.0'),
            port=kwargs.get('port', 8000),
            log_level='error',
        )

        server = uvicorn.Server(config)
        instance = cls(app, server)
        app.add_event_handler("startup", instance.on_startup)
        app.add_event_handler("shutdown", instance.on_shutdown)
        setattr(instance, 'node_id', node_id)
        setattr(instance, 'service_id', service_id)
        asyncio.create_task(server.serve())
        service = asyncio.create_task(instance.start())
        result = await service
        return result

    async def shutdown(
        self,
        dynamic_tasks: list[asyncio.Task],
    ):
        await self.db.disconnect()
        await self.server.shutdown()
        await super().shutdown(dynamic_tasks)

    async def on_startup(self):
        await self.db.connect()
        task_funcs = await self.db.fetch_task_functions()
        try:
            for task_func in task_funcs:
                self.add_service_task_to_router(
                    task_func.service_meta, task_func)
        except Exception as e:
            print(e)
        # self.add_service_rpc_to_router(rpc_func.service_name, rpc_func.func_name)
        # start system event consumer
        # if initialize broker failed, raise exception or warning

    async def on_shutdown(self):
        pass
        # await PrismaClientWrapper.disconnect()

    def add_service_task_to_router(
        self,
        service_meta: ServiceMeta,
        task_function: TaskFunction,
    ):
        self.app.openapi_schema = None
        service_name = to_snake_case(service_meta.name)

        assert not (
            task_function.method and task_function.connection), "Both method and connection cannot be true at the same time."
        # assert task_fuction
        # Include the router in the app
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
                    task_function
                )
            # case WebProtocol.WEBSOCKET:
            #     self.generate_websocket_function(
            #         service_name,
            #         task_fuction
            #     )
            #     print(f"Added Websocket {task_fuction.name} to {service_name}")
        # Reset the OpenAPI schema cache

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
                    raise Exception(
                        "User type parameter is not allowed without auth=True")
                auth_dependency = f"{name}: {type_name} = Depends(get_user), "
            else:
                parameters += f"{name}: {type_name}, "
        if auth_dependency:
            parameters += auth_dependency
        parameters += "service: ApiService = Depends(self.get_service), "
        parameters += "task_function: TaskFunction = Depends(get_task_fuction), "
        # Define the function dynamically
        function_definition = f"""
async def {task_fuction.name}({parameters}):
    params = locals()  # Capture the local variables as a dictionary
    params.pop('service')  # Remove the service parameter
    params.pop('task_function')  # Remove the task parameter
    # # Serialize the parameters to bytes
    serialized_params = pickle.dumps(params)
    response = await service.broker.send_message(
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
        self.app.router.post(
            f'/{service_name}/{task_fuction.name}')(dynamic_function)

    def generate_websocket_function(
        self,
        service_name: str,
        task_fuction: TaskFunction,
    ):
        """
            websocket의 경우 parameter가 user 밖에 없을것이다.
            인증방식은 query parameter로 token을 받아서 처리할것이다.
        """

        async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
            # response channel must be unique for each websocket
            token_data = verify_token(token)
            # user = await get_db().user.find_unique(where={"id": int(token_data.sub)})
            websocket_response_ch = uuid.uuid4().hex

            await websocket.accept()

            async def get_response(websocket: WebSocket):
                async for data in self.broker.listen(websocket_response_ch):
                    # print(f"Received response: {data.decode()}")
                    await websocket.send_text(data.decode())

            response_task = asyncio.create_task(get_response(websocket))
            # add cancel condition
            try:
                while not response_task.done():
                    # TODO update this part
                    receive_data = await websocket.receive_text()
                    if not receive_data:
                        continue
                    data = {
                        "data": receive_data,
                        "user_id": token_data.sub,
                    }
                    await self.broker.async_send_message(
                        task_fuction.queue_name,
                        pickle.dumps(data),
                        websocket_response_ch,
                    )
            except WebSocketDisconnect:
                pass
            if not response_task.done():
                response_task.cancel()

        self.app.router.websocket(
            f'/{service_name}/{task_fuction.name}')(websocket_endpoint)
        print(f"Added Websocket {task_fuction.name} to {service_name}")
        print(f'path: /{service_name}/{task_fuction.name}')
