from enum import IntEnum


class ServiceState(IntEnum):
    PENDING = 1
    ACTIVE = 2
    INACTIVE = 3


class StreamCommand(IntEnum):
    SET_TARGET = 21
    """메세지를 전달 대상을 설정하는 명령어"""
    
    # SET_TARGETS = 22
    # """메세지를 전달 대상을 설정하는 명령어"""
    
    SUBSCRIBE = 24
    """특정 채널을 구독하는 명령어"""
    
    UNSUBSCRIBE = 25
    """특정 채널을 구독 해제하는 명령어"""


class StreamMethod(IntEnum):
    WEBSOCKET = 10
    """WebSocket을 통한 스트림 전송 방식."""
    
    WEBRTC = 11
    """WebRTC를 통한 스트림 전송 방식."""

class StreamCommunicationType(IntEnum):
    SYNC = 1
    """Client가 메세지를 보내면, 동기적으로 단일 클라이언트에게 답장하는 방식"""
    
    ASYNC = 2
    """Client가 메세지를 보내면, 비동기적으로 단일 클라이언트에게 답장하는 방식"""
        
    MULTICAST = 3
    """특정 그룹의 클라이언트에게만 메세지를 보내는 방식"""
    
    PUSH_NOTIFICATION = 4
    """서버가 특정 이벤트 발생 시 Client에게 push notification을 보내는 방식"""

    BROADCAST = 5
    """Client가 메세지를 보내면, 받고 처리 후 모든 클라이언트에게 broadcast 하는 방식"""  

class HttpMethod(IntEnum):
    GET = 10
    """서버로부터 리소스를 조회하는 요청 메서드."""
    
    POST = 11
    """서버에 데이터를 제출하여 리소스를 생성하는 요청 메서드."""
    
    PUT = 12
    """서버에 데이터를 제출하여 리소스를 업데이트하는 요청 메서드."""
    
    DELETE = 13
    """서버로부터 리소스를 삭제하는 요청 메서드."""

class WarpInPhase(IntEnum):
    INITIATION = 14
    """소환 시작 단계"""
    
    CHANNELING = 15
    """에너지를 모으는 단계"""
    
    MATERIALIZATION = 16
    """건물이 구체화되는 단계"""
    
    COMPLETION = 17
    """건물이 완성되는 단계"""

class WarpInTaskResult(IntEnum):
    SUCCESS = 1
    FAIL = 2
    IS_MASTER = 3
    IS_REPLICA = 4
    API_REGISTER_SUCCESS = 5

class ArbiterShutdownTaskResult(IntEnum):
    SUCCESS = 10
    WARNING = 11


class ArbiterCliCommand(IntEnum):
    R = 100
    S = 101
    K = 102
    L = 103
    Q = 104

    def description(self):
        descriptions = {
            ArbiterCliCommand.R: "Reload Arbiter",
            ArbiterCliCommand.S: "Start Service",
            ArbiterCliCommand.K: "Stop Service",
            ArbiterCliCommand.L: "Display services",
            ArbiterCliCommand.Q: "Warp-Out",
        }
        return descriptions[self]

    def get_typer_text(self):
        return f"\t[bold yellow]{self.name.lower()}[/bold yellow]\t{self.description()}"


class ArbiterMessageType(IntEnum):
    # General messages
    PING = 1
    PONG = 2

    SHUTDOWN = 3
    MASTER_SHUTDOWN = 4
    # Arbiter messages
    ARBITER_SERVICE_REGISTER = 5
    ARBITER_SERVICE_REGISTER_ACK = 6
    ARBITER_SERVICE_UNREGISTER = 7
    ARBITER_SERVICE_UNREGISTER_ACK = 8
    ARBITER_SERVICE_STOP = 9
    ARBITER_SERVICE_STOP_ACK = 10

    API_REGISTER = 11
    API_REGISTER_ACK = 12
    API_UNREGISTER = 13
    API_UNREGISTER_ACK = 14

    API_ROUTE_REGISTER = 15
    API_ROUTE_REGISTER_ACK = 16
    API_ROUTE_UNREGISTER = 17
    API_ROUTE_UNREGISTER_ACK = 18
    # # Error messages
    ACK = 19
    ERROR = 100
    
