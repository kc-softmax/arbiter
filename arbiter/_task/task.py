from arbiter.data.models import ArbiterTaskNode
from arbiter.brokers.nats_broker import (
    ArbiterNatsBroker,
    NatsBrokerConfig
)

import multiprocessing
import asyncio
import uuid


class ArbiterTask:
    def __init__(self, name: str, node_id: str, service_id: str) -> None:
        self.name = name
        self.node_id = node_id
        self.service_id = service_id
        self.task_id = uuid.uuid4().hex
        self.broker = ArbiterNatsBroker(
            config=NatsBrokerConfig(),
            name="task",
        )
        self.health_check_interval = 3
        self.task_node = ArbiterTaskNode(
            id=self.task_id,
            node_id=node_id,
            name=self.name,
            state=1,
            queue='',
            service_name=self.service_id
        )

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
                self.task, self.local_health_check_task,
            ], return_when=asyncio.FIRST_COMPLETED)
            for result in unfinished:
                result.cancel()
        except (Exception, asyncio.CancelledError, KeyboardInterrupt) as err:
            print("task", err)
        finally:
            print("task process finished")

    async def start(self):
        idx = 0
        timeout = 1000
        while True:
            await asyncio.sleep(1)
            if idx == timeout:
                break
            idx += 1
        return 'finished'
