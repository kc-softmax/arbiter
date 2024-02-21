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


StreamSystemCallback = Callable[[StreamMeta, str | None], Awaitable[None]]
# 브로커 메시지 콜백 타입
ServiceMessageReceiveCallback = Callable[[StreamMeta, ServiceMessage, str | None], Awaitable[None]]
# 유저 메시지 콜백 타입
UserMessageReceiveCallback = Callable[[StreamMeta, bytes, str | None], Awaitable[None]]
# 에러 콜백 타입
BackgroundErrorCallback = Callable[[Exception, None], Awaitable[None]]


class ArbiterStream:
    def __init__(self, path: str) -> None:
        self.path: str = path
        self.connected_service_ids: dict = {}
        self.socket_connect_callback: StreamSystemCallback = None
        self.socket_close_callback: StreamSystemCallback = None
        self.service_connect_callback: StreamSystemCallback = None
        self.service_receive_callback: ServiceMessageReceiveCallback = None
        self.user_receive_callback: UserMessageReceiveCallback = None
        self.background_error_callback: BackgroundErrorCallback | None = None

    async def _consume(self,
                       user_id: str,
                       connection: ArbiterConnection,
                       producer: MessageProducerInterface,
                       consumer: MessageConsumerInterface):
        connected_service_id = self.connected_service_ids.get(user_id)
        async for message in consumer.listen():
            if connected_service_id is None:
                connected_service_id = message
                self.connected_service_ids[user_id] = message
                # 연결 완료 콜백 실행
                await self.service_connect_callback(
                    StreamMeta(
                        connection=connection,
                        topic=user_id,
                        producer=producer,
                        consumer=consumer,
                    ),
                    connected_service_id,
                )
            else:
                await connection.send_message(message)
                await self.service_receive_callback(
                    StreamMeta(
                        connection=connection,
                        topic=user_id,
                        producer=producer,
                        consumer=consumer
                    ),
                    ServiceMessage(
                        message=message
                    ),
                    connected_service_id,
                )

    async def _monitor_background_task(self, task: asyncio.Task):
        try:
            await task
        except Exception as e:
            if self.background_error_callback:
                self.background_error_callback(e)

    async def _websocket_endpoint(self, token: str, connection: ArbiterConnection):
        async with RedisBroker() as (broker, producer, consumer):
            await connection.websocket.accept()
            try:
                token_data = verify_token(token)
                user_id = token_data.sub

                async with unit_of_work.transaction() as session:
                    user = await game_uesr_repository.get_by_id(session, int(user_id))
                    if user == None:
                        raise Exception("유저를 찾을 수 없습니다.")
                    if user.access_token != token:
                        raise Exception("유효하지 않은 토큰입니다.")

                await consumer.subscribe(user_id)

                consume_task = asyncio.create_task(
                    self._consume(
                        user_id,
                        connection,
                        producer=producer,
                        consumer=consumer,
                    ))
                monitor_task = asyncio.create_task(
                    self._monitor_background_task(consume_task)
                )

                # 소켓 연결 완료 콜백 실행
                await self.socket_connect_callback(
                    StreamMeta(
                        connection=connection,
                        topic=user_id,
                        producer=producer,
                        consumer=consumer,
                    ),
                    None,
                )

                # 유저 메시지 대기
                async for websocket_message in connection.run():
                    # 유저 메시지를 받으면 유저 메시지 콜백 실행
                    await self.user_receive_callback(
                        StreamMeta(
                            connection=connection,
                            topic=user_id,
                            producer=producer,
                            consumer=consumer,
                        ),
                        websocket_message,
                        self.connected_service_ids.get(user_id),
                    )
            except Exception as e:
                print(f"[Stream Error] {e}")
            finally:
                service_id = self.connected_service_ids.pop(user_id)
                # 연결 종료 콜백 실행
                await self.socket_close_callback(
                    StreamMeta(
                        connection=connection,
                        topic=user_id,
                        producer=producer,
                        consumer=consumer,
                    ),
                    service_id,
                )
                if consume_task is not None:
                    consume_task.cancel()
                if monitor_task is not None:
                    monitor_task.cancel()
                await connection.close()

    def start(self):
        @arbiterApp.websocket(self.path)
        async def add_stream(websocket: WebSocket, token: str = Query()):
            await self._websocket_endpoint(token, ArbiterWebsocket(websocket))

    def on_socket_connect(self, callback: StreamSystemCallback) -> StreamSystemCallback:
        self.socket_connect_callback = callback
        return callback

    def on_socket_close(self, callback: StreamSystemCallback) -> StreamSystemCallback:
        self.socket_close_callback = callback
        return callback

    def on_service_connect(self, callback: StreamSystemCallback) -> StreamSystemCallback:
        self.service_connect_callback = callback
        return callback

    def on_service_message_receive(self, callback: ServiceMessageReceiveCallback) -> ServiceMessageReceiveCallback:
        self.service_receive_callback = callback
        return callback

    def on_user_message_receive(self, callback: UserMessageReceiveCallback) -> UserMessageReceiveCallback:
        self.user_receive_callback = callback
        return callback

    def on_background_error(self, callback: BackgroundErrorCallback) -> BackgroundErrorCallback:
        self.background_error_callback = callback
        return callback
