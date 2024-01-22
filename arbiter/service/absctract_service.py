import uuid
import timeit
import asyncio
import collections
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
        self.service_id = uuid.uuid4()
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
    async def subscribe(self, user_id: int, user_name: str):
        pass

    @abstractmethod
    async def unsubscribe(self, user_id: int):
        pass

    @abstractmethod
    async def update_message(self, message: StreamMessage):
        pass

    @abstractmethod
    async def processing(self):
        pass

    async def start(self):
        time_interval = 1 / self.frame_rate
        waiting_time = time_interval
        while True:
            waiting_time > 0 and await asyncio.sleep(waiting_time)
            turn_start_time = timeit.default_timer()
            await self.processing()
            elapsed_time = timeit.default_timer() - turn_start_time
            waiting_time = time_interval - elapsed_time
            self.unused_time += waiting_time

    async def consume(self):
        await self.consumer.subscribe(self.service_id)
        async for message in self.consumer.listen():
            message = StreamMessage.decode_pickle(message)
            print('consume in service: ', message)
            match message.event_type:
                case StreamSystemEvent.SUBSCRIBE:
                    await self.subscribe(message.user_id, message.data)
                    continue
                case StreamSystemEvent.UNSUBSCRIBE:
                    print('unsubscribe', message.user_id)
                    await self.unsubscribe(message.user_id)
                    continue

            await self.update_message(message)
            self.unused_time = 0

    async def producing(self, topic: str, data: bytes):
        # print('produce in service: ', topic, len(data))
        await self.producer.send(topic, data)

    async def __aenter__(self):
        self.consuming_task = asyncio.create_task(self.consume())
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.stop()
        self.consuming_task.cancel()
        await self.consuming_task
