from __future__ import annotations
import asyncio
import multiprocessing
import time
from multiprocessing.synchronize import Event
from arbiter.configs import ArbiterConfig
from arbiter.data.models import ArbiterBaseNode
from arbiter import Arbiter

class AribterTaskNodeRunner:
    
    def __init__(self):
        self.arbiter: Arbiter = None
        self.node: ArbiterBaseNode = None
        
    def get_node_id(self) -> str:
        assert self.node is not None, "Node is not set, please set the node before running the service."
        return self.node.node_id
    
    async def on_init(self, *args, **kwargs):
        pass
    
    async def on_start(self):
        pass

    async def on_shutdown(self):
        pass

    async def on_error(self, error: Exception):
        print("Error in runnig process", error)
    
    def run(
        self,
        queue: multiprocessing.Queue,
        event: Event,
        arbiter_config: ArbiterConfig,
        health_check_interval: int,
        *args,
        **kwargs
    ):
        try:
            asyncio.run(
                self._executor(
                    queue,
                    event,
                    arbiter_config,
                    health_check_interval,
                    *args,
                    **kwargs
                )
            )
        except Exception as e:
            print("Error in run", e, self.__class__.__name__)

    async def _executor(
        self,
        queue: multiprocessing.Queue,
        event: Event,
        arbiter_config: ArbiterConfig,
        health_check_interval: int,
        *args,
        **kwargs
    ):
        try:
            self.arbiter = Arbiter(arbiter_config)
            await self.arbiter.connect()
            loop = asyncio.get_event_loop()
            try:
                await self.on_init(*args, **kwargs)
                health_checker = loop.run_in_executor(
                    None,
                    self._health_check,
                    queue,
                    event,
                    self.node.node_id,
                    health_check_interval)
                task = self()
                executor = asyncio.create_task(task(self.arbiter))
                await self.on_start()
                await asyncio.gather(health_checker, executor)
                await self.on_shutdown()
            except asyncio.CancelledError:
                pass    
            except Exception as e:
                print("Error in health check", e)
            finally:
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
            queue.put(node_id)
            time.sleep(health_check_interval)