from arbiter import ArbiterRunner, ArbiterNode
from arbiter.configs import NatsBrokerConfig, ArbiterNodeConfig
# from tests.service import TestService, TestException, ArbiterService




# ############################################################################################################
app = ArbiterNode(
    config=ArbiterNodeConfig(system_timeout=10),
    # gateway_config=None
)
# app.add_service(TestException())
# app.add_service(TestService())

if __name__ == '__main__':
    ArbiterRunner.run(
        app,
        broker_config=NatsBrokerConfig(),
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
