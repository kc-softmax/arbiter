from __future__ import annotations
import asyncio
import time
import nats
import pickle
from nats.errors import NoRespondersError
from nats.aio.msg import Msg
from typing import Any, AsyncGenerator
from arbiter.exceptions import TaskNotRegisteredError
from arbiter.configs import NatsBrokerConfig
from arbiter.brokers.base import ArbiterBrokerInterface
from arbiter.utils import get_pickled_data
from arbiter.constants import ASYNC_TASK_CLOSE_MESSAGE

class ArbiterNatsBroker(ArbiterBrokerInterface):

    def __init__(
        self,
        *,
        config: NatsBrokerConfig,
        name: str,
        log_level: str = "info",
        log_format: str = "[arbiter] - %(level)s - %(message)s - %(datetime)s",
    ) -> None:
        super().__init__(name=name, log_level=log_level, log_format=log_format)
        self.config = config
        self.nats: nats.NATS = None

    async def connect(self) -> None:
        async def disconnected_cb():
            # print('Got disconnected!')
            pass

        async def reconnected_cb():
            print(f'Got reconnected to {self.nats.connected_url.netloc}')

        async def error_cb(e: Exception):
            print(f'There was an error: {e}')

        async def closed_cb():
            # print('Connection is closed')
            pass
            
        connection_url = f"nats://{self.config.host}:{self.config.port}"
        self.nats = await nats.connect(
            connection_url,
            name=self.name,
            max_reconnect_attempts=self.config.max_reconnect_attempts,
            disconnected_cb=disconnected_cb,
            reconnected_cb=reconnected_cb,
            error_cb=error_cb,
            closed_cb=closed_cb
        )
        
    async def disconnect(self) -> None:
        self.nats and await self.nats.close()
    
    async def request(
        self,
        target: str, 
        message: bytes,
        timeout: int = 0
    ) -> Any:
        try:
            # TODO 
            response = await self.nats.request(target, pickle.dumps(message), timeout=timeout)
            return get_pickled_data(response.data)
        except asyncio.TimeoutError as e:
            print(f"Timeout in request to {target} {e}")
        except NoRespondersError as e:
            print(f"No responders in request to {target} {e}")
            raise TaskNotRegisteredError(f"Task {target} is not registered")
        
        raise Exception(f"Unknown error in request to {target}")
    
    async def stream(
        self,
        target: str,
        message: bytes,
        timeout: int = 0
    ) -> AsyncGenerator[bytes, None]:
        inbox = self.nats.new_inbox()
        sub = await self.nats.subscribe(inbox)
        await self.nats.publish(target, pickle.dumps(message), reply=inbox)
        while True:
            try:
                response = await sub.next_msg(timeout=timeout)
                if not response:
                    break
                if response.data == ASYNC_TASK_CLOSE_MESSAGE:
                    break
                yield get_pickled_data(response.data)
            except Exception as e:
                print(f"Error in stream: {e}")
                raise e
        await sub.unsubscribe()
        
    async def emit(
        self,
        target: str,
        message: bytes | Any
    ) -> None:
        if not isinstance(message, bytes):
            message = pickle.dumps(message)
        await self.nats.publish(target, message)
    
    async def broadcast(
        self,
        target: str,
        message: bytes,
        reply: str = '',
    ) -> None:
        # TODO Consider, get response from all subscribers
        await self.nats.publish(target, pickle.dumps(message), reply)
    
    async def listen(
        self,
        queue: str,
        timeout: int = 0
    ) -> AsyncGenerator[Msg, None]:
        async def message_handler(msg: Msg):
            # 메시지를 받을 때마다 큐에 추가
            await message_queue.put((msg.reply, msg.data))
        # 구독자 생성, subject
        message_queue = asyncio.Queue()
        try:
            sub = await self.nats.subscribe(queue, cb=message_handler)
            while True:
                if timeout:
                    # 큐에서 메시지를 꺼내서 반환
                    message = await asyncio.wait_for(message_queue.get(), timeout=timeout)
                else:
                    message = await message_queue.get()
                yield message    
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"Error in listen: {e}")
        finally:
            try:
                await sub.unsubscribe()
            except Exception as e:
                pass

    async def subscribe_listen(
        self,
        queue: str,
    ) -> AsyncGenerator[bytes, None]:
        sub = await self.nats.subscribe(queue)
        try:
            while True:
                message = await sub.next_msg(None)
                yield (message.reply, message.data)
        except Exception as e:
            print(f"Error in subscribe_listen: {e}")
        finally:
            await sub.unsubscribe()
    
    async def periodic_listen(
        self,
        queue: str,
        interval: float = 1
    ) -> AsyncGenerator[bytes, None]:
        try:
            sub = await self.nats.subscribe(queue)
            while True:
                collected_messages = []
                start_time = time.monotonic()
                while (time.monotonic() - start_time) < interval:
                    # 현재 시간과 시작 시간의 차이를 계산하여 timeout을 조정
                    timeout = interval - (time.monotonic() - start_time)
                    if timeout <= 0:
                        break
                    # 비동기적으로 메시지를 가져옴
                    try:
                        message = await sub.next_msg(1)
                        collected_messages.append(message.data)
                    except Exception as e:
                        pass
                if collected_messages:
                    yield (None, collected_messages)
                else:
                    # 주기 동안 메시지가 없더라도 빈 리스트를 반환
                    yield (None, [])
        except Exception as e:
            print(f"Error in periodic_listen: {e}")
        finally:
            await sub.unsubscribe()