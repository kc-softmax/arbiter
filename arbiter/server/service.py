from contextlib import asynccontextmanager
import json
import os
import uuid
import asyncio


from uvicorn.server import Server
from uvicorn.config import Config

from arbiter import Arbiter
from arbiter.data.models import ArbiterServerNode, ArbiterServerModel
from arbiter.server.app import ArbiterApiApp
from arbiter.service import ArbiterService


class ArbiterServerService(ArbiterService):
    """
        현재는 단순히 ArbiterServiceWorker copy & paste 해서 구현하였지지만,
        Model이 정리된 후 refactoring이 필요합니다.    
    """

    def __init__(
        self,
        server_node_id: str,
        broker_host: str = 'localhost',
        broker_port: int = 6379,
        broker_password: str = None,
        host: str = 'localhost',
        port: int = 8080,
        log_level: str = 'error',
        allow_origins: str = '*',
        allow_methods: str = '*',
        allow_headers: str = '*',
        allow_credentials: bool = True,
    ):
        super().__init__(
            server_node_id,
            broker_host,
            broker_port,
            broker_password
        )                
        
        self.router_task: asyncio.Task = None
        self.app = ArbiterApiApp(
            self.arbiter,
            self.lifespan,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials
        )
        config = Config(
            app=self.app,
            host=host,
            port=port,
            log_level=log_level,
        )
        self.server = Server(config)

    # override witout super
    async def run(self):
        await self.arbiter.connect()
        # each serve() and start() should be run in parallel
        # and communicate shutdown signal to each other
        await asyncio.gather(
            self.server.serve(),
            self.start()
        )        
        await self.shutdown()
        await self.arbiter.disconnect()
        #

    # override
    async def on_start(self):
        self.router_task = asyncio.create_task(self.router_handler())
        assert isinstance(self.service_node, ArbiterServerNode)
        await self.refresh_model()

    @asynccontextmanager
    async def lifespan(self, app: ArbiterApiApp):
        yield
        self.router_task and self.router_task.cancel()
        self.force_stop = True

    async def refresh_model(self):
        server_model = await self.arbiter.get_data(ArbiterServerModel, self.service_node.arbiter_server_model_id)
        assert server_model
        assert isinstance(server_model, ArbiterServerModel)
        for http_task_model in server_model.http_task_models:
            self.app.generate_http_function(http_task_model)
        for stream_task_model in server_model.stream_task_models:
            self.app.generate_stream_function(stream_task_model)
        
    # override
    async def health_check_func(self) -> str:
        await super().health_check_func()
        self.server.should_exit = True
        
    async def router_handler(self):
        async for message in self.arbiter.subscribe_listen(self.arbiter_node.get_routing_channel()):
            try:
                message = message.decode()
                # TODO: message validation
                # TODO: message handling
                print(f"router_handler: {message}")
            except Exception as e:
                print(f"Error in router_handler: {e}")
                continue
            # try:
            #     task_model = ArbiterTaskModel.model_validate_json(message)
            #     service_name = task_model.service_meta.name
            # except Exception as e: # TODO Exception type more detail
            #     print(f"Error in router_handler: {e}")
            #     continue
            # if task_model.method:
            #     method = HttpMethod(task_model.method)
            #     match method:
            #         case HttpMethod.POST:
            #             self.generate_post_function(
            #                 service_name,
            #                 task_model
            #             )
            # elif task_model.connection:
            #     connection = StreamMethod(task_model.connection)
            #     match connection:
            #         case StreamMethod.WEBSOCKET:
            #             self.generate_websocket_function(
            #                 service_name,
            #                 task_model)
            # await self.arbiter.create_data(
            #     WebServiceTask,
            #     web_service_id=self.web_service.id,
            #     task_id=task_model.id
            # )
                
            # self.openapi_schema = None

