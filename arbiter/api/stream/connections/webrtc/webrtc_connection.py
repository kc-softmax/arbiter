from enum import StrEnum
from aiortc import (
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCDataChannel,
    RTCIceCandidate,
)
from pyee import AsyncIOEventEmitter
from fastapi import WebSocket
from arbiter.api.stream.connections.webrtc.signaling import ArbiterSignaling
from arbiter.api.auth.schemas import UserSchema
from arbiter.api.stream.connections.abstract_connection import ArbiterConnection

class RTCStateChangeEvent(StrEnum):
    ICE_CONNECTION = "iceconnectionstatechange"
    PEER_CONNECTION = "connectionstatechange"

class RTCDataChannelEvent(StrEnum):
    OPEN = "open"
    MESSAGE = "message"
    ERROR = "error"

class ArbiterWebRTCEvent(StrEnum):
    CONNECTED = "connected"
    CLOSEED = "closed"
    MESSAGE = "message"

class RTCDataChannelLabel(StrEnum):
    CHAT = "chat"

ice_servers = [
    RTCIceServer(urls="turn:211.119.91.210:3478?transport=tcp",
                 username="softmax",
                 credential="softmax"),
    # RTCIceServer(urls="stun:stun.l.google.com:19302"),
]

class ArbiterWebRTC(ArbiterConnection, AsyncIOEventEmitter):

    def __init__(
        self,
        websocket: WebSocket,
        user: UserSchema,
    ):
        super(ArbiterConnection, self).__init__()
        super(AsyncIOEventEmitter, self).__init__()
        
        self.websocket = websocket
        self.user = user
        self.config = RTCConfiguration(iceServers=ice_servers)
        self.peer_connection = RTCPeerConnection(self.config)
        # 데이터 채널이 여러개 있을 때 어떻게 해야할까?
        self.chat_data_channel: RTCDataChannel = self.peer_connection.createDataChannel(label='chat', negotiated=False)
        self.signaling: ArbiterSignaling = ArbiterSignaling(websocket, self.peer_connection)

        # 이벤트 핸들러 등록
        @self.peer_connection.on(RTCStateChangeEvent.PEER_CONNECTION)
        async def peer_connection_state_changed():
            print(f"connection state {self.peer_connection.connectionState}")
            match self.peer_connection.connectionState:
                case "failed":
                    await self.close()
                case "connected":
                    self.emit(ArbiterWebRTCEvent.CONNECTED)
                case "closed":
                    self.emit(ArbiterWebRTCEvent.CLOSEED)

        @self.chat_data_channel.on(RTCDataChannelEvent.OPEN)
        async def chat_data_channel_opened():
            print("create data channel")
            # temp pong
            self.chat_data_channel.send("hi iam arbiter")

        @self.chat_data_channel.on(RTCDataChannelEvent.MESSAGE)
        async def chat_data_channel_message_received(message: str):
            # callback(StreamMessage(message, self.user))
            self.emit(ArbiterWebRTCEvent.MESSAGE, message)

        @self.chat_data_channel.on(RTCDataChannelEvent.ERROR)
        async def chat_data_channel_error_raised(error: str):
            print(error)
            await self.error(error)

    async def run(self):
        await self.signaling.start()
 
    async def send_message(self, bytes: bytes):
        pass
        # await self.data_channel and await self.data_channel.send(bytes)
    
    def clear(self):
        pass
        
    async def close(self):
        await self.chat_data_channel.close()
        await self.peer_connection.close()
        self.clear()
    
    def error(self, reason: str | None):
        return super().error(reason)
