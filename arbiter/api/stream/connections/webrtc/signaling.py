import os
from fastapi import WebSocket
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    RTCRtpSender,
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
        video_transceiver = self.peer_connection.addTransceiver('video')
        video_codecs = RTCRtpSender.getCapabilities('video').codecs
        video_transceiver.setCodecPreferences(video_codecs)

        audio_transceiver = self.peer_connection.addTransceiver('audio')
        audio_codecs = RTCRtpSender.getCapabilities('audio').codecs
        audio_transceiver.setCodecPreferences(audio_codecs)

        @self.peer_connection.on('icecandidate')
        async def on_icecandidate(candidate):
            if candidate:
                await self.websocket.send_json(object_to_string(candidate))

        # create offer
        offer: RTCSessionDescription = await self.peer_connection.createOffer()       
        await self.peer_connection.setLocalDescription(offer)
        # send offer
        await self.websocket.send_json(object_to_string(offer))


        async for message in self.websocket.iter_text():
            signaling_object: RTCSessionDescription | RTCIceCandidate = object_from_string(message)
            if isinstance(signaling_object, RTCSessionDescription):
                if signaling_object.type == 'offer':
                    answer: RTCSessionDescription = await self.peer_connection.createAnswer()       
                    await self.peer_connection.setLocalDescription(answer)
                    await self.websocket.send_json(object_to_string(answer))
                elif signaling_object.type == 'answer':
                    await self.peer_connection.setRemoteDescription(signaling_object)
            elif isinstance(signaling_object, RTCIceCandidate):
                await self.peer_connection.addIceCandidate(signaling_object)
            elif signaling_object is BYE:
                print("bye~")
            else:
                raise Exception("의도되지 않은 시그널링 메시지입니다.")
