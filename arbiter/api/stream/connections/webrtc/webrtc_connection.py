import typing
from enum import StrEnum
from aiortc import (
    RTCIceServer,
    RTCPeerConnection,
    RTCConfiguration,
    RTCDataChannel,
    RTCRtpSender,
    MediaStreamTrack,
)
from fastapi import WebSocket
from starlette._utils import is_async_callable
from arbiter.api.stream.connections.webrtc.signaling import ArbiterSignaling
from arbiter.api.auth.schemas import UserSchema
from arbiter.api.stream.connections.abstract_connection import ArbiterConnection

class RTCPeerConnectionEvent(StrEnum):
    ICE_CONNECTION_STATE_CHANGE = "iceconnectionstatechange"
    PEER_CONNECTION_STATE_CHANGE = "connectionstatechange"
    TRACK = "track"

class RTCTrackEvent(StrEnum):
    ENDED = "ended"

class RTCDataChannelEvent(StrEnum):
    OPEN = "open"
    MESSAGE = "message"
    ERROR = "error"

class ArbiterWebRTCEvent(StrEnum):
    CONNECTED = "connected"
    CLOSEED = "closed"
    DATA_CHANNEL_OPENED = "data_channel_opened"
    MESSAGE = "message"
    TRACK="track"

class RTCDataChannelLabel(StrEnum):
    CHAT = "chat"

ice_servers = [
    RTCIceServer(urls="turn:211.119.91.210:3478?transport=tcp",
                 username="softmax",
                 credential="softmax"),
    # RTCIceServer(urls="stun:stun.l.google.com:19302"),
]

class ArbiterWebRTC(ArbiterConnection):

    def __init__(
        self,
        websocket: WebSocket,
        user: UserSchema,
    ):
        super(ArbiterConnection, self).__init__()
        
        self.websocket = websocket
        self.user = user
        self.config = RTCConfiguration(iceServers=ice_servers)
        self.peer_connection = RTCPeerConnection(self.config)
        # 데이터 채널이 여러개 있을 때 어떻게 해야할까?
        self.data_channel: RTCDataChannel = self.peer_connection.createDataChannel(label='chat', negotiated=False)
        self.signaling: ArbiterSignaling = ArbiterSignaling(websocket, self.peer_connection)
        # arbiter web rtc 이벤트 핸들러
        self.on_connect: list[typing.Callable] = []
        self.on_message: list[typing.Callable[[str], None]] = []
        self.on_data_channel_open: list[typing.Callable] = []
        self.on_close: list[typing.Callable] = []
        self.on_track: list[typing.Callable[[MediaStreamTrack], None]] = []

        # aiortc 이벤트 핸들러 등록
        @self.peer_connection.on(RTCPeerConnectionEvent.PEER_CONNECTION_STATE_CHANGE)
        async def peer_connection_state_changed():
            print(f"connection state {self.peer_connection.connectionState}")
            match self.peer_connection.connectionState:
                case "failed":
                    await self.close()
                case "connected":
                    await self.emit(ArbiterWebRTCEvent.CONNECTED)
                case "closed":
                    await self.close()
                    await self.emit(ArbiterWebRTCEvent.CLOSEED)
        
        @self.peer_connection.on(RTCPeerConnectionEvent.TRACK)
        async def track_received(track: MediaStreamTrack):
            await self.emit(ArbiterWebRTCEvent.TRACK, track)            

        @self.data_channel.on(RTCDataChannelEvent.OPEN)
        async def data_channel_opened():
            print("create data channel")
            await self.emit(ArbiterWebRTCEvent.DATA_CHANNEL_OPENED)

        @self.data_channel.on(RTCDataChannelEvent.MESSAGE)
        async def data_channel_message_received(message: str):
            # callback(StreamMessage(message, self.user))
            await self.emit(ArbiterWebRTCEvent.MESSAGE, message)

        @self.data_channel.on(RTCDataChannelEvent.ERROR)
        async def data_channel_error_raised(error: str):
            print(error)
            await self.error()

    async def run(self):
        await self.signaling.start()
 
    async def send_message(self, message: str):
        self.data_channel.send(message)
        # await self.data_channel and await self.data_channel.send(bytes)
    
    def clear(self):
        pass
        
    async def close(self):
        self.clear()
        self.data_channel.close()
        await self.peer_connection.close()

    async def error(self, reason: str | None):
        await self.close()
     
    async def emit(self, event_type: str, *args, **kwagrs) -> None:
        handlers: list[typing.Callable] = None
        match event_type:
            case ArbiterWebRTCEvent.CONNECTED:
                handlers = self.on_connect
            case ArbiterWebRTCEvent.MESSAGE:
                handlers = self.on_message
            case ArbiterWebRTCEvent.CLOSEED:
                handlers = self.on_close
            case ArbiterWebRTCEvent.DATA_CHANNEL_OPENED:
                handlers = self.on_data_channel_open
            case ArbiterWebRTCEvent.TRACK:
                handlers = self.on_track

        for handler in handlers:
            if is_async_callable(handler):
                await handler(*args, **kwagrs)
            else:
                handler(*args, **kwagrs)

    def add_event_handler(
        self, 
        event_type: str, 
        func: typing.Callable
    ) -> None: 
        assert event_type in [item.value for item in ArbiterWebRTCEvent]
        match event_type:
            case ArbiterWebRTCEvent.CONNECTED:
                self.on_connect.append(func)
            case ArbiterWebRTCEvent.MESSAGE:
                self.on_message.append(func)
            case ArbiterWebRTCEvent.CLOSEED:
                self.on_close.append(func)
            case ArbiterWebRTCEvent.DATA_CHANNEL_OPENED:
                self.on_data_channel_open.append(func)
            case ArbiterWebRTCEvent.TRACK:
                self.on_track.append(func)

    def on_event(self, event_type: str) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            self.add_event_handler(event_type, func)
            return func
        return decorator

    def subscribe_track(self, track: MediaStreamTrack) -> RTCRtpSender:
        pass