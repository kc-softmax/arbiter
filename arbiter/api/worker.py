from contextlib import asynccontextmanager
import json
import os
import uuid
import asyncio


from uvicorn.server import Server
from uvicorn.config import Config

from arbiter import Arbiter
from arbiter.api.app import ArbiterApiApp
from arbiter.enums import ServiceState
from arbiter.models import WebService, WebServiceTask


class ArbiterUvicornWorker:
    """
        현재는 단순히 ArbiterWorker copy & paste 해서 구현하였지지만,
        Model이 정리된 후 refactoring이 필요합니다.    
    """

    def __init__(
        self,
        node_id: str,
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
        self.web_service: WebService = None
        self.node_id = node_id
        self.force_stop = False
                
        self.system_subscribe_task: asyncio.Task = None
        
        self.health_check_task: asyncio.Task = None        
        self.router_task: asyncio.Task = None
        self.health_check_time = 0
        
        self.arbiter: Arbiter = Arbiter(
            host=broker_host,
            port=broker_port,
            password=broker_password
        )

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

    async def run(self):
        await self.server.serve()

    @asynccontextmanager
    async def lifespan(self, app: ArbiterApiApp):
        await self.arbiter.connect()
        self.router_task = asyncio.create_task(self.router_handler())
        
        # change to register
        """
            WebService 를 만든다,
        
        """
        self.web_service = await self.arbiter.create_data(
            WebService,
            node_id=self.node_id,
            app_id='removed',
            state=ServiceState.ACTIVE
        )
        yield
        self.health_check_task and self.health_check_task.cancel()
        self.router_task and self.router_task.cancel()
        await self.arbiter.disconnect()

    
    async def health_check_func(self) -> str:
        if not self.health_check_time:
            self.health_check_time = asyncio.get_event_loop().time()
        health_check_retry = 0
        while True and not self.force_stop:
            try:
                start_time = asyncio.get_event_loop().time()
                if start_time - self.health_check_time > ARBITER_SERVICE_TIMEOUT:
                    break
                if start_time - self.health_check_time > ARBITER_SERVICE_HEALTH_CHECK_INTERVAL:
                    response = await self.arbiter.send_message(
                        receiver_id=self.node_id,
                        data=ArbiterTypedData(
                            type=ArbiterDataType.PING,
                            data=self.service_id).model_dump_json(),
                        wait_response=True)
                    if response:
                        if response == self.service.shutdown_code:
                            print('Shutdown')
                            return 'Service Shutdown by System'
                        self.health_check_time = asyncio.get_event_loop().time()
                    else:
                        health_check_retry += 1
                        if health_check_retry > HEALTH_CHECK_RETRY:
                            print(
                                f"{self.__class__.__name__} Response Empty, Health Check Failed")
                            break
                        else:
                            print(
                                f"{self.__class__.__name__} Response Empty, Retry {health_check_retry}")
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                return "Health Check Cancelled"
        # print(f"{self.__class__.__name__} Health Check Finished")
        if self.force_stop:
            return 'Force Stop from System'
        return 'Health Check Finished'

    async def get_system_message(self):
        async for message in self.arbiter.subscribe_listen(channel=Node.system_channel(self.node_id)):
            decoded_message = ArbiterTypedData.model_validate_json(message)
            data = decoded_message.data
            match decoded_message.type:
                case ArbiterDataType.SHUTDOWN:
                    self.force_stop = True
                    break#

    async def router_handler(self):
        # message 는 어떤 router로 등록해야 하는가?에 따른다?
        # TODO ADD router, remove Router?
        async for message in self.arbiter.subscribe_listen(Node.routing_channel(self.node_id)):
            if message == b"TEMP_SHUTDOWN":
                await self.arbiter.update_data(
                    self.web_service,
                    state=ServiceState.INACTIVE)
                continue
            try:
                task_model = ArbiterTaskModel.model_validate_json(message)
                service_name = task_model.service_meta.name
            except Exception as e: # TODO Exception type more detail
                print(f"Error in router_handler: {e}")
                continue
            if task_model.method:
                method = HttpMethod(task_model.method)
                match method:
                    case HttpMethod.POST:
                        self.generate_post_function(
                            service_name,
                            task_model
                        )
            elif task_model.connection:
                connection = StreamMethod(task_model.connection)
                match connection:
                    case StreamMethod.WEBSOCKET:
                        self.generate_websocket_function(
                            service_name,
                            task_model)
            await self.arbiter.create_data(
                WebServiceTask,
                web_service_id=self.web_service.id,
                task_id=task_model.id
            )
                
            self.openapi_schema = None

