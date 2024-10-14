from arbiter import ArbiterRunner, ArbiterNode
from arbiter.configs import NatsBrokerConfig, ArbiterNodeConfig
# from tests.service import TestService, TestException, ArbiterService
from tests._service import service

import uvicorn


# ############################################################################################################
app = ArbiterNode(
    config=ArbiterNodeConfig(system_timeout=5),
    # gateway=None,
    gateway_config=uvicorn.Config(app=None, port=8000)
    # gateway=FasiAPI(),
    # gateway_config=Uvico
)
# app.add_service(service)
# app.add_service(TestException())
# app.add_service(TestService())

if __name__ == '__main__':
    ArbiterRunner.run(
        app,
        broker_config=NatsBrokerConfig(),
        # repl=True
    )

# ############################################################################################################
# service = ArbiterService()

# @service.async_task(queue='test_service_return_task')
# async def return_async_task(data: dict) -> dict:
#     pass

# app = ArbiterNode()
# app.add_service(service)

# if __name__ == '__main__':
#     ArbiterRunner.run(
#         app,
#         gateway=ArbiterGatewayService())
    
############################################################################################################
# app = ArbiterNode(
#     gateway=ArbiterFastAPI
# )

# @app.async_task(queue='test_service_return_task')
# async def return_async_task(data: dict) -> dict:

#     pass

# if __name__ == '__main__':
#     ArbiterRunner.run(
#         app,
#         broker_config=NatsBrokerConfig(),
# )
############################################################################################################
