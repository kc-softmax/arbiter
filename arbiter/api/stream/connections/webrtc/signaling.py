from fastapi import WebSocket
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
)
from aiortc.contrib.signaling import BYE, object_from_string, object_to_string

class ArbiterSignaling():
    def __init__(
            self, 
            websocket: WebSocket, 
            peer_connection: RTCPeerConnection) -> None:
        self.websocket: WebSocket = websocket
        self.peer_connection: RTCPeerConnection = peer_connection

    async def start(self):
        # create offer
        offer: RTCSessionDescription = await self.peer_connection.createOffer()       
        await self.peer_connection.setLocalDescription(offer)
        # send offer
        await self.websocket.send_json(object_to_string(offer))
        # recveive answer, cadidate
        async for message in self.websocket.iter_text():
            signaling_object: RTCSessionDescription | RTCIceCandidate = object_from_string(message)
            if isinstance(signaling_object, RTCSessionDescription):
                await self.peer_connection.setRemoteDescription(signaling_object)
            elif isinstance(signaling_object, RTCIceCandidate):
                await self.peer_connection.addIceCandidate(signaling_object)
            elif signaling_object is BYE:
                print("bye~")
            else:
                raise Exception("의도되지 않은 시그널링 메시지입니다.")
