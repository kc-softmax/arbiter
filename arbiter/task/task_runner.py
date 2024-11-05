from __future__ import annotations
import asyncio
import multiprocessing
import time
from multiprocessing.synchronize import Event
from arbiter.configs import ArbiterConfig
from arbiter.data.models import ArbiterBaseNode
from arbiter import Arbiter
from arbiter.enums import NodeState
from arbiter.logger import ArbiterLogger

class AribterTaskNodeRunner:
    
    def __init__(self):
        self.arbiter: Arbiter = None
        self.node: ArbiterBaseNode = None
        self.logger = ArbiterLogger(name=self.__class__.__name__)
        self.logger.add_handler()
        
    def get_node_id(self) -> str:
        assert self.node is not None, "Node is not set, please set the node before running the service."
        return self.node.node_id
    
    async def on_init(
        self,
        event_queue: multiprocessing.Queue,
        *args,
        **kwargs
    ):
        self.node.state = NodeState.PENDING        
        event_queue.put(self.node.encode_node_state())
    
    async def on_start(
        self, 
        event_queue: multiprocessing.Queue,
        *args,
        **kwargs
    ):
        self.node.state = NodeState.ACTIVE
        event_queue.put(self.node.encode_node_state())

    async def on_shutdown(
        self,
        event_queue: multiprocessing.Queue,
        *args,
        **kwargs
    ):
        self.node.state = NodeState.STOPPED
        event_queue.put(self.node.encode_node_state())

    async def on_error(
        self, 
        error: Exception,
        event_queue: multiprocessing.Queue,
        *args,
        **kwargs
    ):
        self.logger.error("Error in runnig process", error)
        self.node.state = NodeState.STOPPED
        event_queue.put(self.node.encode_node_state())
    
    def run(
        self,
        health_check_queue: multiprocessing.Queue,
        event_queue: multiprocessing.Queue,
        event: Event,
        arbiter_config: ArbiterConfig,
        health_check_interval: int,
        task_close_timeout: int,
        *args,
        **kwargs
    ):
        try:
            asyncio.run(
                self._executor(
                    health_check_queue,
                    event_queue,
                    event,
                    arbiter_config,
                    health_check_interval,
                    task_close_timeout,
                    *args,
                    **kwargs
                )
            )
        except Exception as e:
            self.logger.error(f"Error in run {e} {self.__class__.__name__}")

    async def _executor(
        self,
        health_check_queue: multiprocessing.Queue,
        event_queue: multiprocessing.Queue,
        event: Event,
        arbiter_config: ArbiterConfig,
        health_check_interval: int,
        *args,
        **kwargs
    ):
        try:
            if _task_close_timeout := kwargs.get("task_close_timeout", None):
                task_close_timeout = _task_close_timeout
            else:
                task_close_timeout = arbiter_config.default_task_close_timeout
            self.arbiter = Arbiter(arbiter_config)
            await self.arbiter.connect()
            loop = asyncio.get_event_loop()
            try:
                await self.on_init(event_queue)
                health_checker = loop.run_in_executor(
                    None,
                    self._health_check,
                    health_check_queue,
                    event,
                    self.node.node_id,
                    health_check_interval)
                task = self()
                executor = asyncio.create_task(task(self.arbiter))
                await self.on_start(event_queue)
                await health_checker
                if executor:
                    executor.cancel()
                    try:
                        await asyncio.wait_for(executor, timeout=task_close_timeout)
                    except asyncio.CancelledError:
                        pass
            except asyncio.CancelledError:
                pass    
            except Exception as e:
                self.logger.error(f"Error in health check {e}")
            finally:
                await self.on_shutdown(event_queue)
            
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
