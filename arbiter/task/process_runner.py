from __future__ import annotations
import asyncio
import multiprocessing
import time
from multiprocessing.synchronize import Event
from arbiter.configs import ArbiterConfig
from arbiter.data.models import ArbiterBaseNode
from arbiter import Arbiter


class ProcessRunner:
    
    def __init__(self):
        self.arbiter: Arbiter = None
        self.node: ArbiterBaseNode = None
        
    def get_node_id(self) -> str:
        assert self.node is not None, "Node is not set, please set the node before running the service."
        return self.node.node_id
    
    async def on_start(self):
        pass

    async def on_shutdown(self):
        pass
    
    async def setup(self):
        raise NotImplementedError("Please implement the setup method.")
    
    async def on_error(self, error: Exception):
        pass
    
    def run(
        self,
        queue: multiprocessing.Queue,
        event: Event,
        arbiter_config: ArbiterConfig,
        health_check_interval: int,
    ):
        try:
            asyncio.run(
                self._run(
                    queue,
                    event,
                    arbiter_config,
                    health_check_interval
                )
            )
        except Exception as e:
            print("Error in run", e, self.__class__.__name__)
        
    async def _run(
        self,
        queue: multiprocessing.Queue,
        event: Event,
        arbiter_config: ArbiterConfig,
        health_check_interval: int,
    ):
        """
        Run the service.
        """
        try:
            self.arbiter = Arbiter(arbiter_config)
            await self.arbiter.connect()
            await self.setup()
            await self.on_start()
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(
                None,
                self._health_check,
                queue,
                event,
                self.node.node_id,
                health_check_interval)
            except asyncio.CancelledError:
                pass    
            except Exception as e:
                print("Error in health check", e)
            await self.on_shutdown()
        except Exception as e:
            await self.on_error(e)
        finally:
            await self.arbiter.disconnect()

    def _health_check(
        self,
        queue: multiprocessing.Queue,
        event: Event,
        node_id: str,
        health_check_interval: int,        
    ):
        while not event.is_set():
            queue.put_nowait(node_id)
            time.sleep(health_check_interval)