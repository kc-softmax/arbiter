import uuid
from aiortc import (
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCDataChannel,
    RTCIceCandidate
)
from aiortc.contrib.signaling import BYE, object_from_string
from aiortc.sdp import (
    candidate_from_sdp,
    parameters_from_sdp,
    parameters_to_sdp)

# using absolute path?
from ..abstract_connection import (
    ArbiterConnection,
    Callable,
    StreamMessage,
    Coroutine,
    WebSocket,
    GameUser
)


class ArbiterWebRTC(ArbiterConnection):

    def __init__(
        self,
        websocket: WebSocket,
        game_user: GameUser,
    ):
        self.websocket: WebSocket = websocket
        self.game_user: GameUser = game_user
        self.data_channel: RTCDataChannel = None

    async def run(self, callback: Callable[[StreamMessage], Coroutine]):
        peer_connection = RTCPeerConnection()

        data_channel = peer_connection.createDataChannel(
            label="arbiter", negotiated=True)

        @data_channel.on("open")
        async def on_open():
            self.data_channel = data_channel
            print("create data channel")

        @data_channel.on("message")
        async def on_message(message: str):
            callback(StreamMessage(message, self.game_user))

        @data_channel.on("error")
        async def on_error(error: str):
            print(error)

        # send offer
        await peer_connection.setLocalDescription(await peer_connection.createOffer())
        await self.websocket.send(peer_connection.localDescription)

        async for message in self.websocket.iter_text():
            signaling_object: RTCSessionDescription | RTCIceCandidate | BYE = object_from_string(
                message)
            if isinstance(signaling_object, RTCSessionDescription):
                await peer_connection.setRemoteDescription(signaling_object)
            elif isinstance(signaling_object, RTCIceCandidate):
                await peer_connection.addIceCandidate(signaling_object)
            elif signaling_object is BYE:
                print("bye~")
                break

    async def send_message(self, bytes: bytes):
        await self.data_channel and await self.data_channel.send(bytes)
