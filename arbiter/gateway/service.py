from contextlib import asynccontextmanager
import asyncio
from typing import Any
from uvicorn.server import Server
from uvicorn.config import Config
from arbiter.gateway.app import ArbiterApiApp
from arbiter.service import ArbiterService
from typing_extensions import Annotated, Doc, deprecated
from arbiter.enums import NodeState
from arbiter.data.models import (
    ArbiterGatewayNode,
    ArbiterTaskNode
)
from arbiter import Arbiter

class ArbiterGatewayService(ArbiterService):
    """
    Gateway service for Arbiter.
    
    **Parameters**
    - `name` (str): The name of the gateway, default is node name.
    - `host` (str): The host of the gateway, default is 'localhost'.
    - `port` (int): The port of the gateway, default is 8080.
    - `load_timeout` (int): The timeout of loading service, default is 10.
    - `log_level` (str): The log level of the service, default is 'info'.
    - `log_format` (str): The log format of the service, default is "[gateway] - %(level)s - %(message)s - %(datetime)s".
    - `allow_origins` (str): The allow origins of the service, default is '*'.
    - `allow_methods` (str): The allow methods of the service, default is '*'.
    - `allow_headers` (str): The allow headers of the service, default is '*'.
    - `allow_credentials` (bool): The allow credentials of the service, default is True.
    
    ## Example
    ```python
    from arbiter import ArbiterRunner, ArbiterNode
    ```
    """
    
    def __init__(
        self,
        *,
        name: str,
        host: str = 'localhost',
        port: int = 8080,
        load_timeout: int = 10,
        options: dict[str, Any] = {
            "allow_origins": '*',
            "allow_methods": '*',
            "allow_headers": '*',
            "allow_credentials": True,
            "log_level": None,
            "log_format": None,
        },
        log_level: str | None = None,
        log_format: str | None = None,
    ):
        super().__init__(
            name=name,
            load_timeout=load_timeout,
            auto_start=True,
            log_level=log_level,
            log_format=log_format,
        )
        self.router_task: asyncio.Task = None
        self.app: ArbiterApiApp = None
        self.server: Server = None
        self.app = ArbiterApiApp(
            self.arbiter,
            self.lifespan,
            **options
        )
        config = Config(
            app=self.app,
            host=host,
            port=int(port),
            log_level=log_level,
        )
        self.server = Server(config)
        self.node: ArbiterGatewayNode = ArbiterGatewayNode(
            name=name,
            state=NodeState.PENDING,
            host=host,
            port=port,
            options=options
        )

    async def setup(
        self,
        arbiter_name: str,
        service_node_id: str,
        arbiter_host: str,
        arbiter_port: int,
        arbiter_config: dict,
    ):
        self.service_node_id = service_node_id
        self.arbiter = Arbiter(
            arbiter_name,
            arbiter_host,
            arbiter_port,
            arbiter_config
        )

    # override witout super
    async def run(self):
        await self.arbiter.connect()
        # each serve() and start() should be run in parallel
        # and communicate shutdown signal to each other
        try:
            await asyncio.gather(
                self.server.serve(),
                self.start()
            )
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()
            await self.arbiter.disconnect()

    # async def _get_service_node(self) -> ArbiterGatewayNode:
    #     return await self.arbiter.get_data(ArbiterGatewayNode, self.service_node_id)

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
        # gateway_model = await self.arbiter.get_data(
        #     ArbiterGatewayModel, self.service_node.parent_model_id)
        
        # # find all service models
        # # gateway 가 없는 경우 다 등록한다.
        # # gateway 가 있는 경우 gateway 가 일치하는 경우 등록한다.
        # public_service_models = await self.arbiter.search_data(
        #     ArbiterServiceModel,
        #     gateway_model_id='')
        # matched_service_models = await self.arbiter.search_data(
        #     ArbiterServiceModel,
        #     gateway_model_id=gateway_model.id)
        # target_service_models = public_service_models + matched_service_models
        # for service_model in target_service_models:
        #     for task_model_id in service_model.task_model_ids:
        #         if task_model := await self.arbiter.get_data(
        #             ArbiterTaskModel,
        #             task_model_id
        #         ):
        #             if task_model.http:
        #                 self.app.generate_http_function(task_model)
        #             # elif task_model.connection:
        #             #     self.app.generate_stream_function(task_model)
        #         # self.app.generate_http_function(http_task_model)
        
        
        pass
        
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

