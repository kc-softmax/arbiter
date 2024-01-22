from __future__ import annotations
import inspect
import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from asyncio.tasks import Task
from typing import Any, Callable, Coroutine, Tuple
from contextlib import asynccontextmanager
from collections import defaultdict
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from arbiter.api.auth.repository import game_uesr_repository
from arbiter.api.auth.utils import verify_token
from arbiter.api.stream.const import StreamSystemEvent
from arbiter.api.stream.data import StreamMessage
from arbiter.api.stream.connections import ArbiterConnection, ArbiterWebsocket, ArbiterWebRTC
from arbiter.api.dependencies import unit_of_work
from arbiter.broker.base import MessageConsumerInterface, MessageProducerInterface


class ArbiterStream:

    def __init__(self):
        # 소켓 연결, 방 입장/퇴장 등과 관련된 이벤트 핸들러들
        # self.config = config
        self.producer: MessageProducerInterface = None
        self.evnet_handlers: dict[
            str, Callable[[Any, str], Coroutine | None]] = defaultdict()

    @asynccontextmanager
    async def connect(
        self,
        websocket: WebSocket,
        producer: MessageProducerInterface,
        consumer: MessageConsumerInterface,
        token: str
    ) -> Tuple[ArbiterConnection, str, str]:
        await websocket.accept()
        try:
            self.producer = producer
            token_data = verify_token(token)
            user_id = token_data.sub
            async with unit_of_work.transaction() as session:
                user = await game_uesr_repository.get_by_id(session, int(user_id))
                if user == None:
                    raise Exception("유저를 찾을 수 없습니다.")
                if user.access_token != token:
                    raise Exception("유효하지 않은 토큰입니다.")

            connection = ArbiterWebsocket(websocket, user)
            await consumer.subscribe(user.id)
            await self.produce(StreamMessage(
                user.id,
                user.user_name,
                event_type=StreamSystemEvent.SUBSCRIBE
            ))
            consumer_task = asyncio.create_task(
                self.consume(consumer, connection))
            await self.run_event_handler(StreamSystemEvent.VALIDATE, user_id)
            yield connection, user_id, user.user_name
            # await until connection close
        except Exception as e:
            yield None, None, None
        finally:
            await self.produce(StreamMessage(
                user.id,
                0,
                event_type=StreamSystemEvent.UNSUBSCRIBE
            ))
            consumer_task.cancel()
            await connection.close()

    async def consume(
        self,
        consumer: MessageConsumerInterface,
        connection: ArbiterConnection
    ):
        async for message in consumer.listen():
            await connection.send_message(message)

    async def produce(self, message: StreamMessage):
        # message send broker how to define target?
        print('produce in stream: ', message)
        await self.producer.send('di', message.encode_pickle())
        # print('produce in stream: ', message)

        # async with broker.subscribe() as messages:
        #     async for message in messages:
        #         print(message)
        #         # message decode 하고 뭔지 살펴본 뒤
        #         await self.connection.send_message(message)
        #     pass
        # case LiveSystemEvent.KICK_USER:
        #     if connection := self.connections.get(message.target, None):
        #         connection.state = LiveConnectionState.CLOSE
        #         if connection.websocket.application_state == WebSocketState.CONNECTED:
        #             await connection.websocket.close()
        #         await self.run_event_handler(LiveSystemEvent.KICK_USER, message.target)
        # case LiveSystemEvent.SAVE_USER_RECORD:
        #     await self.run_event_handler(LiveSystemEvent.SAVE_USER_RECORD, message.target, message.data)
        # case LiveSystemEvent.ERROR:
        #     # TODO: error handling
        #     # if target is None ->  send all users
        #     pass

    # stream_event broker

    def on_event(self, event_type: StreamSystemEvent):
        def callback_wrapper(callback: Callable):
            self.evnet_handlers[event_type] = callback
            return callback
        return callback_wrapper

    async def run_event_handler(self, event_type: StreamSystemEvent, *args):
        event_handlers = self.evnet_handlers
        handler = event_handlers.get(event_type)
        match event_type:
            case added_event if added_event in event_handlers.keys():
                if handler:
                    if inspect.iscoroutinefunction(handler):
                        await handler(*args)
                    else:
                        handler(*args)

    async def handle_system_message(self, message: StreamMessage):
        # 무엇에 쓰는것인고?
        pass

    def close_stream(self):
        pass
