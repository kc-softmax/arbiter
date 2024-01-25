from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable
from fastapi import Query, WebSocket
from arbiter.api.auth.repository import game_uesr_repository
from arbiter.api.auth.utils import verify_token
from arbiter.api.dependencies import unit_of_work
from arbiter.api.stream.connections import ArbiterConnection, ArbiterWebsocket
from arbiter.broker.base import MessageConsumerInterface, MessageProducerInterface
from arbiter.broker.redis_broker import RedisBroker
from arbiter.api import arbiterApp

@dataclass(kw_only=True)
class StreamMeta:
    connection: ArbiterConnection
    topic: str
    producer: MessageProducerInterface
    consumer: MessageConsumerInterface

# temp
@dataclass(kw_only=True)
class ServiceMessage:
    message: any

StreamSystemCallback = Callable[[StreamMeta], Awaitable[None]]
# 브로커 메시지 콜백 타입
ServiceMessageReceiveCallback = Callable[[StreamMeta, ServiceMessage], Awaitable[None]]
# 유저 메시지 콜백 타입
UserMessageReceiveCallback = Callable[[StreamMeta, bytes], Awaitable[None]]
# 에러 콜백 타입
BackgroundErrorCallback = Callable[[Exception, None], Awaitable[None]]

class ArbiterStream:
    def __init__(self, path: str) -> None:
        self.path: str = path
        self.topic: str = None
        self.connection: ArbiterConnection = None
        self.start_callback: StreamSystemCallback = None
        self.close_callback: StreamSystemCallback = None
        self.service_receive_callback: ServiceMessageReceiveCallback = None
        self.user_receive_callback: UserMessageReceiveCallback = None
        self.background_error_callback: BackgroundErrorCallback | None = None
    
    async def _consume(self, 
                       producer: MessageProducerInterface, 
                       consumer: MessageConsumerInterface):
        async for message in consumer.listen():
            await self.connection.send_message(message)
            await self.service_receive_callback(
                StreamMeta(
                    connection=self.connection,
                    topic=self.topic,
                    producer=producer,
                    consumer=consumer
                ),
                ServiceMessage(
                    message=message
                )
            )

    async def _monitor_background_task(self, task: asyncio.Task):
        try:
            await task
        except Exception as e:
            if self.background_error_callback:
                await self.background_error_callback(e)

    async def _websocket_endpoint(self, token:str= Query()):
        assert self.connection is not None

        async with RedisBroker() as (broker, producer, consumer):
            await self.connection.websocket.accept()   
            try:
                token_data = verify_token(token)
                user_id = token_data.sub

                async with unit_of_work.transaction() as session:
                    user = await game_uesr_repository.get_by_id(session, int(user_id))
                    if user == None:
                        raise Exception("유저를 찾을 수 없습니다.")
                    if user.access_token != token:
                        raise Exception("유효하지 않은 토큰입니다.")
                
                # 자신 토픽 id 등록
                self.topic = user_id
                # 자신 토픽 id 구독
                await consumer.subscribe(self.topic)
                consume_task = asyncio.create_task(
                    self._consume(
                        producer=producer,
                        consumer=consumer
                    ))
                monitor_task = asyncio.create_task(
                    self._monitor_background_task(consume_task)
                )

                stream_meta = StreamMeta(
                    connection=self.connection,
                    topic=self.topic,
                    producer=producer,
                    consumer=consumer
                )

                # 연결 완료 콜백 실행
                await self.start_callback(stream_meta)

                # 유저 메시지 대기
                async for websocket_message in self.connection.run():
                    # 유저 메시지를 받으면 유저 메시지 콜백 실행
                    await self.user_receive_callback(
                        stream_meta,
                        websocket_message
                    )
            except Exception as e:
                print(f"[Stream Error] {e}")
            finally:
                # 연결 종료 콜백 실행
                await self.close_callback(stream_meta)
                if consume_task is not None:
                    consume_task.cancel()
                if monitor_task is not None:
                    monitor_task.cancel()
                self.connection.close()

    def start(self):
        @arbiterApp.websocket(self.path)
        async def add_stream(websocket: WebSocket, token:str= Query()):
            # 지금은 websocket connection 단일
            self.connection = ArbiterWebsocket(websocket)
            await self._websocket_endpoint(token)

    def on_start(self, callback: StreamSystemCallback) -> StreamSystemCallback:
        self.start_callback = callback
        return callback

    def on_close(self, callback: StreamSystemCallback) -> StreamSystemCallback:
        self.close_callback = callback
        return callback
    
    def on_service_message_receive(self, callback: ServiceMessageReceiveCallback) -> ServiceMessageReceiveCallback:
        self.service_receive_callback = callback
        return callback
    
    def on_user_message_receive(self, callback: UserMessageReceiveCallback) -> UserMessageReceiveCallback:
        self.user_receive_callback= callback
        return callback

    def on_background_error(self, callback: BackgroundErrorCallback) -> BackgroundErrorCallback:
        self.background_error_callback= callback
        return callback
