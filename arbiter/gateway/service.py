from contextlib import asynccontextmanager
import asyncio
from uvicorn.server import Server
from uvicorn.config import Config
from arbiter.gateway.app import ArbiterApiApp
from arbiter.service import ArbiterService, ArbiterServiceInfo
from arbiter.data.models import (
    ArbiterGatewayModel,
    ArbiterGatewayNode,
    ArbiterServiceModel,
    ArbiterTaskModel
)

class ArbiterGatewayServiceInfo(ArbiterServiceInfo):
    
    def __init__(self, klass: type, *args, **kwargs):
        super().__init__(klass, *args, **kwargs)
        self.host = kwargs.get('host', 'localhost')
        self.port = kwargs.get('port', 8080)
        self.log_level = kwargs.get('log_level', 'error')
        self.allow_origins = kwargs.get('allow_origins', '*')
        self.allow_methods = kwargs.get('allow_methods', '*')
        self.allow_headers = kwargs.get('allow_headers', '*')
        self.allow_credentials = kwargs.get('allow_credentials', True)
        
class ArbiterGatewayService(ArbiterService):

    @classmethod
    def get_service_info_class(cls):
        return ArbiterGatewayServiceInfo

    def __init__(
        self,
        arbiter_name: str,
        service_node_id: str,
        arbiter_host: str,
        arbiter_port: int,
        arbiter_config: dict,
        host: str,
        port: int,
        log_level: str,
        allow_origins: str,
        allow_methods: str,
        allow_headers: str,
        allow_credentials: bool,
    ):
        super().__init__(
            arbiter_name,
            service_node_id,
            arbiter_host,
            int(arbiter_port),
            arbiter_config
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
            port=int(port),
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

    async def _get_service_node(self) -> ArbiterGatewayNode:
        return await self.arbiter.get_data(ArbiterGatewayNode, self.service_node_id)

    # override
    async def on_start(self):
        self.router_task = asyncio.create_task(self.router_handler())
        assert isinstance(self.service_node, ArbiterGatewayNode)
        await self.refresh_tasks()

    @asynccontextmanager
    async def lifespan(self, app: ArbiterApiApp):
        yield
        self.router_task and self.router_task.cancel()
        self.force_stop = True

    async def refresh_tasks(self):
        gateway_model = await self.arbiter.get_data(
            ArbiterGatewayModel, self.service_node.parent_model_id)
        
        # find all service models
        # gateway 가 없는 경우 다 등록한다.
        # gateway 가 있는 경우 gateway 가 일치하는 경우 등록한다.
        public_service_models = await self.arbiter.search_data(
            ArbiterServiceModel,
            gateway_model_id='')
        matched_service_models = await self.arbiter.search_data(
            ArbiterServiceModel,
            gateway_model_id=gateway_model.id)
        target_service_models = public_service_models + matched_service_models
        for service_model in target_service_models:
            for task_model_id in service_model.task_model_ids:
                if task_model := await self.arbiter.get_data(
                    ArbiterTaskModel,
                    task_model_id
                ):
                    if task_model.http:
                        self.app.generate_http_function(task_model)
                    # elif task_model.connection:
                    #     self.app.generate_stream_function(task_model)
                # self.app.generate_http_function(http_task_model)
        
        
        # assert server_model
        # assert isinstance(server_model, ArbiterServerModel)
        # for http_task_model in server_model.http_task_models:
        #     self.app.generate_http_function(http_task_model)
        # for stream_task_model in server_model.stream_task_models:
        #     self.app.generate_stream_function(stream_task_model)
        # self.server.re
        
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

