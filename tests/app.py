from arbiter import ArbiterRunner, ArbiterNode
from arbiter.configs import NatsBrokerConfig, ArbiterNodeConfig, ArbiterConfig
# from tests.service import TestService, TestException, ArbiterService
from tests._service import service
from fastapi import FastAPI

import uvicorn


# ############################################################################################################
app = ArbiterNode(
    arbiter_config=ArbiterConfig(broker_config=NatsBrokerConfig()),
    node_config=ArbiterNodeConfig(system_timeout=5),
    # gateway=FastAPI(),
    gateway=None
    # gateway=uvicorn.Config(app=FastAPI(), port=8000)
)
# app.add_service(service)
# app.add_service(TestException())
# app.add_service(TestService())

if __name__ == '__main__':
    ArbiterRunner.run(
        app,
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
