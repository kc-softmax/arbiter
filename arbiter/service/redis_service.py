from arbiter.service import AbstractService
from arbiter import Arbiter


class RedisService(AbstractService[Arbiter]):

    def __init__(
        self,
        name: str,
        node_id: str,
        service_id: str,
    ):
        super().__init__(
            name,
            node_id, 
            service_id,
            Arbiter)

    # async def incoming_task_func(self) -> str:
    #     # RPC
    #     while True:
    #         request_json = await self.broker.client.blpop(
    #             self.__class__.__name__, timeout=0)
    #         if request_json:
    #             message = 0
    #             # try:
    #             #     message = ArbiterMessage.decode(request_json[1])
    #             #     from_service_id = message.from_service_id
    #             #     response = None
    #             # except Exception as e:
    #             #     print('Error: ', e)
    #             # response = ArbiterMessage(
    #             #     from_service_id=ARBITER_SYSTEM_SERVICE_ID,
    #             #     message_type=ArbiterDataType.ERROR,
    #             #     payload=str(e)
    #             # )
    #             # response and await self.redis_broker.client.set(
    #             #     from_service_id,
    #             #     response.encode()
    #             # )
    #         else:
    #             # Timeout 발생
    #             # Arbiter 상태 확인
    #             # Arbiter Shutdown
    #             print('Timeout break, Arbiter Shutdown')
    #             break

    #     # await self.broker.subscribe(self.service_id)
    #     # async for message in self.broker.listen():
    #     #     await self.get_message(message)
    #     # await self.broker.unsubscribe(self.service_id)
    #     return 'Incomig Task finished'
