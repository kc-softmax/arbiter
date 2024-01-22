from __future__ import annotations
from dataclasses import dataclass
import asyncio
from typing import Awaitable, Callable
from fastapi import Query, WebSocket
from fastapi.websockets import WebSocketState
from arbiter.api.auth.repository import game_uesr_repository
from arbiter.api.auth.utils import verify_token
from arbiter.api.stream.const import StreamSystemEvent
from arbiter.api.stream.data import StreamMessage
from arbiter.api.dependencies import unit_of_work
from arbiter.broker.base import MessageConsumerInterface, MessageProducerInterface
from arbiter.broker.redis_broker import RedisBroker
from arbiter.api import arbiterApp

# class ArbiterStream:

#     def __init__(self):
#         # 소켓 연결, 방 입장/퇴장 등과 관련된 이벤트 핸들러들
#         # self.config = config
#         self.producer: MessageProducerInterface = None
#         self.evnet_handlers: dict[
#             str, Callable[[Any, str], Coroutine | None]] = defaultdict()

#     @asynccontextmanager
#     async def connect(
#         self,
#         websocket: WebSocket,
#         producer: MessageProducerInterface,
#         consumer: MessageConsumerInterface,
#         token: str
#     ) -> Tuple[ArbiterConnection, str, str]:
#         await websocket.accept()
#         try:
#             self.producer = producer
#             token_data = verify_token(token)
#             user_id = token_data.sub
#             async with unit_of_work.transaction() as session:
#                 user = await game_uesr_repository.get_by_id(session, int(user_id))
#                 if user == None:
#                     raise Exception("유저를 찾을 수 없습니다.")
#                 if user.access_token != token:
#                     raise Exception("유효하지 않은 토큰입니다.")

#             connection = ArbiterWebsocket(websocket, user)
#             await consumer.subscribe(user.id)
#             await self.produce(StreamMessage(
#                 user.id,
#                 user.user_name,
#                 event_type=StreamSystemEvent.SUBSCRIBE
#             ))
#             consumer_task = asyncio.create_task(
#                 self.consume(consumer, connection))
#             await self.run_event_handler(StreamSystemEvent.VALIDATE, user_id)
#             yield connection, user_id, user.user_name
#             # await until connection close
#         except Exception as e:
#             yield None, None, None
#         finally:
#             await self.produce(StreamMessage(
#                 user.id,
#                 0,
#                 event_type=StreamSystemEvent.UNSUBSCRIBE
#             ))
#             consumer_task.cancel()
#             await connection.close()

#     async def consume(
#         self,
#         consumer: MessageConsumerInterface,
#         connection: ArbiterConnection
#     ):
#         async for message in consumer.listen():
#             await connection.send_message(message)

#     async def produce(self, message: StreamMessage):
#         # message send broker how to define target?
#         print('produce in stream: ', message)
#         await self.producer.send('di', message.encode_pickle())
#         # print('produce in stream: ', message)

#         # async with broker.subscribe() as messages:
#         #     async for message in messages:
#         #         print(message)
#         #         # message decode 하고 뭔지 살펴본 뒤
#         #         await self.connection.send_message(message)
#         #     pass
#         # case LiveSystemEvent.KICK_USER:
#         #     if connection := self.connections.get(message.target, None):
#         #         connection.state = LiveConnectionState.CLOSE
#         #         if connection.websocket.application_state == WebSocketState.CONNECTED:
#         #             await connection.websocket.close()
#         #         await self.run_event_handler(LiveSystemEvent.KICK_USER, message.target)
#         # case LiveSystemEvent.SAVE_USER_RECORD:
#         #     await self.run_event_handler(LiveSystemEvent.SAVE_USER_RECORD, message.target, message.data)
#         # case LiveSystemEvent.ERROR:
#         #     # TODO: error handling
#         #     # if target is None ->  send all users
#         #     pass

#     # stream_event broker

#     def on_event(self, event_type: StreamSystemEvent):
#         def callback_wrapper(callback: Callable):
#             self.evnet_handlers[event_type] = callback
#             return callback
#         return callback_wrapper

#     async def run_event_handler(self, event_type: StreamSystemEvent, *args):
#         event_handlers = self.evnet_handlers
#         handler = event_handlers.get(event_type)
#         match event_type:
#             case added_event if added_event in event_handlers.keys():
#                 if handler:
#                     if inspect.iscoroutinefunction(handler):
#                         await handler(*args)
#                     else:
#                         handler(*args)

#     async def handle_system_message(self, message: StreamMessage):
#         # 무엇에 쓰는것인고?
#         pass

#     def close_stream(self):
#         pass

##########################################################
@dataclass(kw_only=True)
class StreamMeta:
    websocket: WebSocket
    topic: str
    producer: MessageProducerInterface
    consumer: MessageConsumerInterface

# temp
@dataclass(kw_only=True)
class ServiceMessage:
    message: any

# 기본 콜백 타입
StreamSystemCallback = Callable[[StreamMeta], Awaitable[None]]
# 브로커 메시지 콜백 타입
ServiceMessageReceiveCallback = Callable[[StreamMeta, ServiceMessage], Awaitable[None]]
# 유저 메시지 콜백 타입
UserMessageReceiveCallback = Callable[[StreamMeta, bytes], Awaitable[None]]

class ArbiterStream2:
    def __init__(self, path:str) -> None:
        self.path = path
        self.topic = None
        self.start_callback: StreamSystemCallback = None
        self.close_callback: StreamSystemCallback = None
        self.service_receive_callback: ServiceMessageReceiveCallback = None
        self.user_receive_callback: UserMessageReceiveCallback = None
    
    async def _consume(self, 
                       websocket: WebSocket, 
                       producer: MessageProducerInterface, 
                       consumer: MessageConsumerInterface):
        async for message in consumer.listen():
            await websocket.send_bytes(message)
            # TODO 멈춤
            # await self.service_receive_callback(
            #     StreamMeta(
            #         websocket=websocket,
            #         topic=self.topic,
            #         producer=producer,
            #         consumer=consumer
            #     ),
            #     ServiceMessage()
            # )

    async def _websocket_endpoint(self, websocket: WebSocket, token:str= Query()):
        async with RedisBroker() as (broker, producer, consumer):                              
            await websocket.accept()   
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
                        websocket=websocket,
                        producer=producer,
                        consumer=consumer
                    ))

                stream_meta = StreamMeta(
                    websocket=websocket,
                    topic=self.topic,
                    producer=producer,
                    consumer=consumer
                )

                # 연결 완료 콜백 실행
                await self.start_callback(stream_meta)

                # 유저 메시지 대기
                async for websocket_message in websocket.iter_bytes():
                    # 유저 메시지를 받으면 유저 메시지 콜백 실행
                    await self.user_receive_callback(
                        stream_meta,
                        websocket_message
                    )
            finally:
                if consume_task is not None:
                    consume_task.cancel()
                if (websocket.state is WebSocketState.CONNECTED):
                    await websocket.close()
                # 연결 종료 콜백 실행
                    await self.close_callback(stream_meta)

    def start(self):
        @arbiterApp.websocket(self.path)
        async def add_stream(websocket: WebSocket, token:str= Query()):
            await self._websocket_endpoint(websocket, token)

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
