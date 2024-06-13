from fastapi import WebSocket
from arbiter.api import arbiterApp
from arbiter.api.auth.schemas import UserSchema
from arbiter.api.stream.connections import ArbiterWebRTC
from arbiter.api.stream.connections.webrtc.webrtc_connection import ArbiterWebRTCEvent

@arbiterApp.websocket('/chat')
async def temp_chat(websocket: WebSocket):
    await websocket.accept()
    temp_user = UserSchema(id=1, email="choi@gmail.com", password="1234", hash_tag=1)
    arbiter_web_rtc_connection = ArbiterWebRTC(websocket, temp_user)
    
    @arbiter_web_rtc_connection.on(ArbiterWebRTCEvent.CONNECTED)
    def connected():
        print("arbiter web rtc connected!")
    
    @arbiter_web_rtc_connection.on(ArbiterWebRTCEvent.CLOSEED)
    def closed():
        print("arbiter web rtc closed!")
    
    @arbiter_web_rtc_connection.on(ArbiterWebRTCEvent.MESSAGE)
    def recevied_message(message: str):
        print(f"arbiter web rtc receive message: {message}")
        
    await arbiter_web_rtc_connection.run()