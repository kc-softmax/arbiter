# import uvicorn
# from typing import Awaitable, Callable, Optional, Union
# from fastapi import APIRouter, FastAPI, Query, WebSocket, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.exceptions import RequestValidationError
# from fastapi.responses import JSONResponse
# from fastapi.websockets import WebSocketState

# from arbiter.api.auth.router import router as auth_router
# from arbiter.api.exceptions import BadRequest
# from arbiter.api.stream import ArbiterStream
# from arbiter.api.auth.dependencies import get_user
# from arbiter.broker import RedisBroker
# from arbiter.utils import to_snake_case
# from arbiter.database import (
#     Database,
#     ServiceMeta,
#     TaskFunction,
#     User
# )


# class ArbiterApiApp(FastAPI):

#     @classmethod
#     async def launch(
#         cls,
#         **kwargs
#     ):
#         instance = cls()
#         config = uvicorn.Config(
#             instance,
#             host=kwargs.get('host', '0.0.0.0'),
#             port=kwargs.get('port', 8080),
#             log_level='error',
#         )
#         server = uvicorn.Server(config)
#         # asyncio.create_task(server.serve())

#         # return result

#     def __init__(self) -> None:
#         self.add_event_handler("startup", self.on_startup)
#         self.add_event_handler("shutdown", self.on_shutdown)
#         self.add_exception_handler(
#             RequestValidationError,
#             lambda request, exc: JSONResponse(
#                 status_code=BadRequest.STATUS_CODE,
#                 content={"detail": BadRequest.DETAIL}
#             )
#         )
#         self.add_middleware(
#             CORSMiddleware,
#             allow_origins='*',
#             allow_credentials=True,
#             allow_methods='*',
#             allow_headers='*'
#         )
#         # app.add_middleware(BaseHTTPMiddleware, dispatch=log_middleware)
#         self.include_router(auth_router)
#         self.db = Database.get_db()
#         self.broker: RedisBroker = RedisBroker()
#         self.services_routers: dict[str, APIRouter] = {}
#         self.stream_handlers: dict[str, Callable[[
#             ArbiterStream], Awaitable[None]]] = {}

#     async def on_startup(self):
#         await self.broker.connect()
#         rpc_funcs = await self.db.fetch_task_functions()
#         try:
#             for rpc_func in rpc_funcs:
#                 self.add_service_rpc_to_router(rpc_func.service_meta, rpc_func)
#         except Exception as e:
#             print(e)

#     async def on_shutdown(self):
#         await self.broker.disconnect()

#     def add_service_rpc_to_router(
#         self,
#         service_meta: ServiceMeta,
#         task_fuction: TaskFunction,
#     ):
#         def get_task_fuction() -> TaskFunction:
#             return task_fuction
#         service_name = to_snake_case(service_meta.name)
#         task_func_name = task_fuction.name
#         if service_name not in self.services_routers:
#             self.services_routers[service_name] = APIRouter(
#                 prefix=f"/services/{service_name}")

#         router = self.services_routers[service_name]
#         # Print the parameters of the function
#         # Construct the parameter list string for the function definition
#         parameters = ""
#         auth_dependency = ""
#         for name, type_name in task_fuction.parameters:
#             if type_name == "User":
#                 if not task_fuction.auth:
#                     raise Exception(
#                         "User type parameter is not allowed without auth=True")
#                 auth_dependency = f"{name}: {type_name} = Depends(get_user), "
#             else:
#                 parameters += f"{name}: {type_name}, "
#         if auth_dependency:
#             parameters += auth_dependency
#         parameters += "service: ApiService = Depends(self.get_service), "
#         parameters += "task_function: TaskFunction = Depends(get_task_fuction), "
#         # Define the function dynamically
#         function_definition = f"""
# async def {task_func_name}({parameters}):
#     params = locals()  # Capture the local variables as a dictionary
#     params.pop('service')  # Remove the service parameter
#     params.pop('task_function')  # Remove the task parameter
#     # # Serialize the parameters to bytes
#     serialized_params = pickle.dumps(params)
#     response = await service.broker.send_message(
#         task_function.queue_name,
#         serialized_params # Use the serialized bytes
#     )
#     if not response:
#         return {{"message": "Failed to get response"}}
#     return {{"message": f"{{response}}"}}
# """
#         local_context = {
#             'get_user': get_user,
#             'get_task_fuction': get_task_fuction,
#             'Depends': Depends,
#             'Union': Union,
#             'User': User,
#             'Optional': Optional,
#             'self': self
#         }
#         # Execute the dynamic function definition
#         exec(function_definition, globals(), local_context)
#         # Retrieve the dynamically defined function
#         dynamic_function = local_context[task_func_name]

#         # Add the endpoint to the router
#         router.post(f'/{task_func_name}')(dynamic_function)

#         # Include the router in the app
#         self.include_router(router)

#     def stream(self, path: str) -> Callable[[Callable[[ArbiterStream], Awaitable[None]]], None]:
#         async def connect_stream(websocket: WebSocket, token: str = Query()):
#             stream = await ArbiterStream.create(websocket, token, self.broker)
#             try:
#                 await self.stream_handlers[path](stream)  # 스트림 핸들러 호출
#             except Exception as e:
#                 print(f"WebSocket connection error: {e}")
#             finally:
#                 if websocket.client_state is WebSocketState.CONNECTED:
#                     # show warning message that we recommend to close connection in stream
#                     await websocket.close()

#         def decorator(handler: Callable[[ArbiterStream], Awaitable[None]]) -> None:
#             self.stream_handlers[path] = handler
#             self.websocket(path)(connect_stream)

#         return decorator
