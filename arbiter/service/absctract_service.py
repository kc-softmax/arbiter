from asyncio import exceptions
import timeit
import asyncio
from abc import ABC, abstractmethod
from arbiter.api.stream.data import StreamMessage, StreamSystemEvent
from arbiter.broker.base import MessageConsumerInterface, MessageProducerInterface


class AbstractService(ABC):

    def __init__(
        self,
        producer: MessageProducerInterface,
        consumer: MessageConsumerInterface,
        frame_rate: int = 30,  # TODO hz? some
    ):
        self.frame_rate = frame_rate
        self.producer = producer
        self.consumer = consumer
        self.consuming_task: asyncio.Task = None
        self.expire_time: int = 60 * 60 * 24
        self.unused_time: int = 0

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def subscribe(self, user_id: int, data: bytes):
        pass

    @abstractmethod
    async def unsubscribe(self, user_id: int):
        pass

    @abstractmethod
    async def update_message(self, message: StreamMessage):
        pass

    @abstractmethod
    async def processing(self) -> bool:
        pass

    async def start(self):
        time_interval = 1 / self.frame_rate
        waiting_time = time_interval
        while True:
            waiting_time > 0 and await asyncio.sleep(waiting_time)
            turn_start_time = timeit.default_timer()
            is_continue = await self.processing()
            if is_continue is False:
                return
            elapsed_time = timeit.default_timer() - turn_start_time
            waiting_time = time_interval - elapsed_time
            self.unused_time += waiting_time

    async def consume(self):
        await self.consumer.subscribe(self.service_id)
        async for message in self.consumer.listen():
            message = StreamMessage.decode_pickle(message)
            # print(f'consume in service #{self.service_id}: ', message)
            match message.event_type:
                case StreamSystemEvent.SUBSCRIBE:
                    print(f'subscribe in service #{self.service_id}:', message.user_id)
                    await self.subscribe(message.user_id, message.data)
                    continue
                case StreamSystemEvent.UNSUBSCRIBE:
                    print(f'unsubscribe in service #{self.service_id}:', message.user_id)
                    await self.unsubscribe(message.user_id)
                    continue

            await self.update_message(message)
            self.unused_time = 0

    def consume_task_done_callback(self, task: asyncio.Task[None]):
        try:
            exception = task.exception()
            print(f"[{self.service_id}] Exception: {exception}")
        except exceptions.CancelledError:
            pass

    async def producing(self, topic: str, data: bytes):
        # print('produce in service: ', topic, len(data))
        await self.producer.send(topic, data)

    async def __aenter__(self):
        self.consuming_task = asyncio.create_task(self.consume())
        self.consuming_task.add_done_callback(self.consume_task_done_callback)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()
        await self.consumer.unsubscribe(self.service_id)
        # await self.consuming_task
        if not self.consuming_task.done():
            self.consuming_task.cancel()
        print(f"[{self.service_id}] DONE!!")
