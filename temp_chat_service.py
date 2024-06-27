from fastapi import WebSocket
from random import randint
from json import dumps
from aiortc import MediaStreamTrack
from arbiter.api import arbiterApp
from arbiter.api.auth.schemas import UserSchema
from arbiter.api.stream.connections import ArbiterWebRTC
from arbiter.api.stream.connections.webrtc.webrtc_connection import ArbiterWebRTCEvent


# TEMP 서버에서 커넥션을 직접 관리하면서 브로드캐스팅하는 점에서 웹소켓을 사용하는 것과 차이가 없음
arbiter_rtc_dict: dict[str, ArbiterWebRTC] = {}

@arbiterApp.websocket('/chat')
async def temp_chat(websocket: WebSocket):
    await websocket.accept()
    me = UserSchema(id=randint(0,1000), email="choi@gmail.com", password="1234", hash_tag=1)
    my_rtc_connection = ArbiterWebRTC(websocket, me)

    @my_rtc_connection.on_event(ArbiterWebRTCEvent.CONNECTED)
    def connected():
        print("arbiter web rtc connected!")
        arbiter_rtc_dict[me.id] = my_rtc_connection
    
    @my_rtc_connection.on_event(ArbiterWebRTCEvent.CLOSEED)
    def closed():
        print("arbiter web rtc closed!")
        arbiter_rtc_dict.pop(me.id)
    
    @my_rtc_connection.on_event(ArbiterWebRTCEvent.DATA_CHANNEL_OPENED)
    def data_channel_opened():
        print("arbiter data channel opened!")
        
    @my_rtc_connection.on_event(ArbiterWebRTCEvent.MESSAGE)
    async def recevied_message(message: str):
        print(f"arbiter web rtc receive message: {message}")
        for user_id, rtc_connection in arbiter_rtc_dict.items():
             if user_id != me.id:
                 await rtc_connection.send_message(dumps({"user_id": me.id, "text": message}))
    
    @my_rtc_connection.on_event(ArbiterWebRTCEvent.TRACK)
    async def track_added(track: MediaStreamTrack):
        print(f"arbiter on track: {track.id}")
        for other_user_id, other_rtc_connection in arbiter_rtc_dict.items():
             if other_user_id != me.id:
                sender = other_rtc_connection.peer_connection.addTrack(track)
                for sender in other_rtc_connection.peer_connection.getSenders():
                    if sender.track and track.kind == sender.track.kind:
                        my_rtc_connection.peer_connection.addTrack(sender.track)
                
    await my_rtc_connection.run()