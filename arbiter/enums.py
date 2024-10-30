from enum import IntEnum

class NodeState(IntEnum):
    PENDING = 1
    ACTIVE = 2
    INACTIVE = 3
    ERROR = 4
    WORKING = 5
    STOPPED = 6
    
class ServiceState(IntEnum):
    PENDING = 1
    ACTIVE = 2
    INACTIVE = 3
    STOPPED = 4

class ExternalNodeEvent(IntEnum):
    NODE_CONNECT = 1
    """새로운 외부 노드가 연결되었을 때 발생하는 이벤트"""
    NODE_DISCONNECT = 2
    """외부 노드가 연결을 해제했을 때 발생하는 이벤트"""
    NODE_RECONNECT = 3
    """외부 노드가 재연결을 시도할 때 발생하는 이벤트(현재는 사용 X)"""
    NODE_UPDATE = 4
    """외부 노드의 정보가 업데이트 되었을 때 발생하는 이벤트"""
    NODE_HEALTH_CHECK = 5
    """외부 노드의 상태를 체크하는 이벤트"""
    TASK_STATE_UPDATE = 6
    """외부 노드의 TASK 상태가 업데이트 되었을 때 발생하는 이벤트"""
    TASK_UPDATE = 7
    """외부 노드의 TASK 정보가 업데이트 되었을 때 발생하는 이벤트"""

class StreamCommand(IntEnum):
    SET_TARGET = 21
    """메세지를 전달 대상을 설정하는 명령어"""    
    SUBSCRIBE = 22
    """특정 채널을 구독하는 명령어"""
    UNSUBSCRIBE = 23
    """특정 채널을 구독 해제하는 명령어"""

# class StreamMethod(IntEnum):
#     WEBSOCKET = 10
#     """WebSocket을 통한 스트림 전송 방식."""
    
#     WEBRTC = 11
#     """WebRTC를 통한 스트림 전송 방식."""

# class StreamCommunicationType(IntEnum):
#     SYNC_UNICAST = 1
#     """Client가 메세지를 보내면, 동기적으로 단일 클라이언트에게 답장하는 방식"""
    
#     ASYNC_UNICAST = 2
#     """Client가 메세지를 보내면, 비동기적으로 단일 클라이언트에게 답장하는 방식"""
        
#     MULTICAST = 3
#     """특정 그룹의 클라이언트에게만 메세지를 보내는 방식"""
    
#     PUSH_NOTIFICATION = 4
#     """서버가 특정 이벤트 발생 시 Client에게 push notification을 보내는 방식"""

#     BROADCAST = 5
#     """Client가 메세지를 보내면, 받고 처리 후 모든 클라이언트에게 broadcast 하는 방식"""  

# class HttpMethod(IntEnum):
#     GET = 10
#     """서버로부터 리소스를 조회하는 요청 메서드."""
    
#     POST = 11
#     """서버에 데이터를 제출하여 리소스를 생성하는 요청 메서드."""

class WarpInPhase(IntEnum):
    PREPARATION = 10
    """소환 준비 단계"""
    
    INITIATION = 14
    """소환 시작 단계"""
        
    MATERIALIZATION = 15
    """건물이 구체화되는 단계"""
    
    DISAPPEARANCE = 16
    """완료 후 사라지는 단계"""
    
class WarpInTaskResult(IntEnum):
    SUCCESS = 1
    FAIL = 2
    WARNING = 3
    INFO = 4

class ArbiterCliCommand(IntEnum):
    R = 100
    H = 101
    Q = 104

    def description(self):
        descriptions = {
            ArbiterCliCommand.R: "Reload Arbiter",
            ArbiterCliCommand.H: "Help",
            ArbiterCliCommand.Q: "Warp-Out",
        }
        return descriptions[self]

    def get_typer_text(self):
        return f"\t[bold yellow]{self.name.lower()}[/bold yellow]\t{self.description()}"

class ArbiterDataType(IntEnum):
    # General messages
    PING = 1

    SHUTDOWN = 3
    MASTER_SHUTDOWN = 4
    # Arbiter messages
    ARBITER_SERVICE_REGISTER = 5
    ARBITER_SERVICE_UNREGISTER = 7
    ARBITER_SERVICE_STOP_REQUEST = 9

    API_REGISTER = 11
    API_UNREGISTER = 13

    API_ROUTE_REGISTER = 15
    API_ROUTE_UNREGISTER = 17
    # # Error messages
    ACK = 19
    NACK = 20
    ERROR = 100