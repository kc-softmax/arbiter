from arbiter import ArbiterRunner, ArbiterNode
from arbiter.configs import NatsBrokerConfig, ArbiterNodeConfig, ArbiterConfig
# from tests.service import TestService, TestException, ArbiterService
# from examples.simple_telemetry.main import TracerSingleton as tracer
from fastapi import FastAPI

import uvicorn


# ############################################################################################################
app = ArbiterNode(
    arbiter_config=ArbiterConfig(broker_config=NatsBrokerConfig()),
    node_config=ArbiterNodeConfig(system_timeout=5),
    # gateway=uvicorn.Config(app=None, port=8001),
    # gateway=None
    # gateway=uvicorn.Config(app=FastAPI(), port=8080)
)

@app.async_task()
async def simple_async_stream(x: int):
    return 4
    # for i in range(5):
    #     yield {"result": "success_stream + " + str(x + i)}

@app.http_task()
async def simple_http_stream(x: int):
    for i in range(5):
        yield {"result": "success_stream + " + str(x + i)}


@app.http_task()
async def simple_http_task(x: int):
    return {"result": "success + " + str(x)}


if __name__ == '__main__':
    ArbiterRunner.run(
        app,
        # reload=True
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
