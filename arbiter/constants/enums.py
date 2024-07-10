from enum import Enum, auto


class ServiceState(Enum):
    PENDING = auto()
    ACTIVE = auto()
    INACTIVE = auto()


class StreamMethod(Enum):
    WEBSOCKET = auto()
    """WebSocket을 통한 스트림 전송 방식."""
    
    WEBRTC = auto()
    """WebRTC를 통한 스트림 전송 방식."""

class StreamCommunicationType(Enum):
    SYNC_UNICAST = auto()
    """Client가 메세지를 보내면, sync적으로 단일 클라이언트에게 답장하는 방식"""
    
    ASYNC_UNICAST = auto()
    """Client가 메세지를 보내면, 비동기적으로 단일 클라이언트에게 답장하는 방식"""
        
    MULTICAST = auto()
    """특정 그룹의 클라이언트에게만 메세지를 보내는 방식"""
    
    PUSH_NOTIFICATION = auto()
    """서버가 특정 이벤트 발생 시 Client에게 push notification을 보내는 방식"""

    BROADCAST = auto()
    """Client가 메세지를 보내면, 받고 처리 후 모든 클라이언트에게 broadcast 하는 방식"""  

class HttpMethod(Enum):
    GET = auto()
    """서버로부터 리소스를 조회하는 요청 메서드."""
    
    POST = auto()
    """서버에 데이터를 제출하여 리소스를 생성하는 요청 메서드."""
    
    PUT = auto()
    """서버에 데이터를 제출하여 리소스를 업데이트하는 요청 메서드."""
    
    DELETE = auto()
    """서버로부터 리소스를 삭제하는 요청 메서드."""

class WarpInPhase(Enum):
    INITIATION = auto()   
    """소환 시작 단계"""
    
    CHANNELING = auto()
    """에너지를 모으는 단계"""
    
    MATERIALIZATION = auto()
    """건물이 구체화되는 단계"""
    
    COMPLETION = auto()
    """건물이 완성되는 단계"""

class WarpInTaskResult(Enum):
    SUCCESS = auto()
    FAIL = auto()
    IS_MASTER = auto()
    IS_REPLICA = auto()
    API_REGISTER_SUCCESS = auto()

class ArbiterShutdownTaskResult(Enum):
    SUCCESS = auto()
    WARNING = auto()


class ArbiterCliCommand(Enum):
    R = auto()
    S = auto()
    K = auto()
    L = auto()
    Q = auto()

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


class ArbiterMessageType(Enum):
    # General messages
    PING = auto()
    PONG = auto()

    SHUTDOWN = auto()
    MASTER_SHUTDOWN = auto()
    # Arbiter messages
    ARBITER_SERVICE_REGISTER = auto()
    ARBITER_SERVICE_REGISTER_ACK = auto()
    ARBITER_SERVICE_UNREGISTER = auto()
    ARBITER_SERVICE_UNREGISTER_ACK = auto()
    ARBITER_SERVICE_STOP = auto()
    ARBITER_SERVICE_STOP_ACK = auto()

    API_REGISTER = auto()
    API_REGISTER_ACK = auto()
    API_UNREGISTER = auto()
    API_UNREGISTER_ACK = auto()

    API_ROUTE_REGISTER = auto()
    API_ROUTE_REGISTER_ACK = auto()
    API_ROUTE_UNREGISTER = auto()
    API_ROUTE_UNREGISTER_ACK = auto()
    # # Error messages
    ERROR = auto()