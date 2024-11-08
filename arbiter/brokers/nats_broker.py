from __future__ import annotations
import asyncio
import time
import nats
import pickle
from nats.errors import NoRespondersError
from nats.aio.msg import Msg
from typing import Any, AsyncGenerator
from arbiter.exceptions import TaskNotRegisteredError
from arbiter.brokers.base import ArbiterBrokerInterface
from arbiter.utils import get_pickled_data
from arbiter.constants import ASYNC_TASK_CLOSE_MESSAGE
from arbiter.logger import ArbiterLogger


class ArbiterNatsBroker(ArbiterBrokerInterface):

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        max_reconnect_attempts: int,
        name: str,
        log_level: str = "info",
        log_format: str = "[arbiter] - %(level)s - %(message)s - %(datetime)s",
    ) -> None:
        super().__init__(name=name, log_level=log_level, log_format=log_format)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.max_reconnect_attempts = max_reconnect_attempts
        self.nats: nats.NATS = None
        self.logger = ArbiterLogger(name=self.__class__.__name__)
        self.logger.add_handler()

    async def connect(self) -> None:
        async def disconnected_cb():
            pass

        async def reconnected_cb():
            self.logger.info(f'Got reconnected to {self.nats.connected_url.netloc}')

        async def error_cb(e: Exception):
            self.logger.error(f'There was an error: {e}')

        async def closed_cb():
            pass
            
        connection_url = f"nats://{self.host}:{self.port}"
        self.nats = await nats.connect(
            connection_url,
            name=self.name,
            user=self.user,
            password=self.password,
            max_reconnect_attempts=self.max_reconnect_attempts,
            
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
            self.logger.error(f"Timeout in request to {target} {e}")
        except NoRespondersError as e:
            self.logger.error(f"No responders in request to {target} {e}")
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
                self.logger.error(f"Error in stream: {e}")
                raise e
        await sub.unsubscribe()
        
    async def emit(
        self,
        target: str,
        message: bytes | Any,
        reply: str = ''
    ) -> None:
        if not isinstance(message, bytes):
            message = pickle.dumps(message)
        await self.nats.publish(target, message, reply)
    
    async def broadcast(
        self,
        target: str,
        message: bytes | Any,
        reply: str = '',
    ) -> None:
        # TODO Consider, get response from all subscribers
        await self.nats.publish(target, pickle.dumps(message), reply)
    
    async def listen(
        self,
        subject: str,
        message_queue: asyncio.Queue,        
        timeout: int = 0,
        # add event
    ) -> AsyncGenerator[Msg, None]:
        async def message_handler(msg: Msg):
            # 메시지를 받을 때마다 큐에 추가
            await message_queue.put((msg.reply, msg.data))
        # 구독자 생성, subject
        try:
            sub = await self.nats.subscribe(subject, cb=message_handler)
            while True:
                if timeout:
                    # 큐에서 메시지를 꺼내서 반환
                    message = await asyncio.wait_for(message_queue.get(), timeout=timeout)
                else:
                    message = await message_queue.get()
                if message is None:
                    break
                yield message    
        except asyncio.TimeoutError:
            self.logger.error("Timeout in listen")
            pass
        except Exception as e:
            self.logger.error(f"Error in listen: {e}")
        finally:
            try:
                await sub.unsubscribe()
            except Exception as e:
                pass

    async def subscribe_listen(
        self,
        subject: str,
        message_queue: asyncio.Queue,        
    ) -> AsyncGenerator[bytes, None]:
        async def message_handler(msg: Msg):
            # 메시지를 받을 때마다 큐에 추가
            await message_queue.put((msg.reply, msg.data))
        # 구독자 생성, subject
        try:
            sub = await self.nats.subscribe(subject, cb=message_handler)
            while True:
                message = await message_queue.get()
                if message is None:
                    break
                yield message    
        except Exception as e:
            self.logger.error(f"Error in listen: {e}")
        finally:
            try:
                await sub.unsubscribe()
            except Exception as e:
                pass
    
    async def periodic_listen(
        self,
        subject: str,
        message_queue: asyncio.Queue,        
        interval: float = 1
    ) -> AsyncGenerator[bytes, None]:
        async def message_handler(msg: Msg):
            # 메시지를 받을 때마다 큐에 추가
            await message_queue.put(msg.data)
        shutdown = False
        try:
            sub = await self.nats.subscribe(subject, cb=message_handler)
            while not shutdown:
                collected_messages = []
                start_time = time.monotonic()
                while (time.monotonic() - start_time) < interval:
                    # 현재 시간과 시작 시간의 차이를 계산하여 timeout을 조정
                    timeout = interval - (time.monotonic() - start_time)
                    if timeout <= 0:
                        break
                    # 비동기적으로 메시지를 가져옴
                    try:
                        # min timeout 0.03
                        if timeout < 0.03:
                            timeout = 0.03
                        message_data = await asyncio.wait_for(
                            message_queue.get(),
                            timeout=timeout)
                        if message_data is None:
                            shutdown = True
                            break
                        collected_messages.append(message_data)
                    except Exception as e:
                        pass
                if collected_messages:
                    yield (None, collected_messages)
                else:
                    # 주기 동안 메시지가 없더라도 빈 리스트를 반환
                    yield (None, [])
        except Exception as e:
            self.logger.error(f"Error in periodic_listen: {e}")
        finally:
            try:
                await sub.unsubscribe()
            except Exception as e:
                pass