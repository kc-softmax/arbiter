from arbiter.data.models import ArbiterServiceNode
from arbiter.brokers.nats_broker import (
    ArbiterNatsBroker,
    NatsBrokerConfig
)
from arbiter._task import ArbiterTask

import multiprocessing
import uuid
import asyncio


class ArbiterService:
    def __init__(self, name: str, node_id: str):
        self.name = name
        self.node_id = node_id
        self.service_id = uuid.uuid4().hex
        self.broker = ArbiterNatsBroker(
            config=NatsBrokerConfig(),
            name="service",
        )
        self.tasks: list[ArbiterTask] = []
        self.health_check_interval = 3
        self.service_node = ArbiterServiceNode(
            id=self.service_id,
            arbiter_node_id=self.node_id,
            name=self.name,
            state=1,
        )

    def add_task(self, task: ArbiterTask):
        self.tasks.append(task)

    async def local_health_check(self, queue: multiprocessing.Queue):
        while True:
            await asyncio.sleep(self.health_check_interval)
            await asyncio.to_thread(queue.put, obj=self.name)

    async def run(self, queue: multiprocessing.Queue):
        try:
            # self.broker = await self.get_broker()
            self.task = asyncio.create_task(self.start())
            self.local_health_check_task = asyncio.create_task(self.local_health_check(queue))
            finished, unfinished = await asyncio.wait([
                self.task, self.local_health_check_task
            ], return_when=asyncio.FIRST_COMPLETED)
            for result in unfinished:
                result.cancel()
        except (Exception, asyncio.CancelledError, KeyboardInterrupt) as err:
            print("service", err)
        finally:
            print("service process finished")

    async def start(self):
        while True:
            await asyncio.sleep(1)
            # print("running service ->", self.service_id)
