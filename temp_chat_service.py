from fastapi import WebSocket
from random import randint
from json import dumps
from arbiter.api import arbiterApp
from arbiter.api.auth.schemas import UserSchema
from arbiter.api.stream.connections import ArbiterWebRTC
from arbiter.api.stream.connections.webrtc.webrtc_connection import ArbiterWebRTCEvent


# TEMP 서버에서 커넥션을 직접 관리하면서 브로드캐스팅하는 점에서 웹소켓을 사용하는 것과 차이가 없음
arbiter_rtc_dict: dict[str, ArbiterWebRTC] = {}

@arbiterApp.websocket('/chat')
async def temp_chat(websocket: WebSocket):
    await websocket.accept()
    temp_user = UserSchema(id=randint(0,1000), email="choi@gmail.com", password="1234", hash_tag=1)
    arbiter_web_rtc_connection = ArbiterWebRTC(websocket, temp_user)
    
    @arbiter_web_rtc_connection.on_event(ArbiterWebRTCEvent.CONNECTED)
    def connected():
        print("arbiter web rtc connected!")
        arbiter_rtc_dict[temp_user.id] = arbiter_web_rtc_connection
    
    @arbiter_web_rtc_connection.on_event(ArbiterWebRTCEvent.CLOSEED)
    def closed():
        print("arbiter web rtc closed!")
        arbiter_rtc_dict.pop(temp_user.id)
    
    @arbiter_web_rtc_connection.on_event(ArbiterWebRTCEvent.DATA_CHANNEL_OPENED)
    def data_channel_opened():
        print("arbiter data channel opened!")
        
    @arbiter_web_rtc_connection.on_event(ArbiterWebRTCEvent.MESSAGE)
    async def recevied_message(message: str):
        print(f"arbiter web rtc receive message: {message}")
        for user_id, rtc_connection in arbiter_rtc_dict.items():
             if user_id != temp_user.id:
                 await rtc_connection.send_message(dumps({"user_id": temp_user.id, "text": message}))
        
    await arbiter_web_rtc_connection.run()