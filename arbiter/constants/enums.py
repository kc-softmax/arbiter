from enum import Enum, auto


class ServiceState(Enum):
    PENDING = auto()
    ACTIVE = auto()
    INACTIVE = auto()


class StreamMethod(Enum):
    WEBSOCKET = 10    # WebSockets for real-time communication
    WEBRTC = 11       # Web Real-Time Communication


class HttpMethod(Enum):
    GET = 1
    POST = 2
    PUT = 3
    DELETE = 4


class ArbiterMessageType(Enum):
    # General messages
    PING = auto()
    PONG = auto()

    SHUTDOWN = auto()
    # Arbiter messages
    ARBITER_SERVICE_REGISTER = auto()
    ARBITER_SERVICE_REGISTER_ACK = auto()
    ARBITER_SERVICE_UNREGISTER = auto()
    ARBITER_SERVICE_UNREGISTER_ACK = auto()
    ARBITER_SERVICE_STOP = auto()
    ARBITER_SERVICE_STOP_ACK = auto()

    API_ROUTE_REGISTER = auto()
    API_ROUTE_REGISTER_ACK = auto()
    API_ROUTE_UNREGISTER = auto()
    API_ROUTE_UNREGISTER_ACK = auto()
    # # Error messages
    ERROR = auto()

    # # Worker messages
    # WORKER_REGISTER = 20
    # WORKER_REGISTER_ACK = 21
    # WORKER_UNREGISTER = 22
    # WORKER_UNREGISTER_ACK = 23
    # WORKER_GET = 24
    # WORKER_GET_ACK = 25

    # # Task messages
    # TASK_SUBMIT = 30
    # TASK_SUBMIT_ACK = 31
    # TASK_CANCEL = 32
    # TASK_CANCEL_ACK = 33
    # TASK_GET = 34
    # TASK_GET_ACK = 35

    # # Result messages
    # RESULT_SUBMIT = 40
    # RESULT_SUBMIT_ACK = 41
    # RESULT_GET = 42
    # RESULT_GET_ACK = 43

    # # Internal messages
    # INTERNAL = 60


class ArbiterInitTaskResult(Enum):
    SUCCESS = auto()
    FAIL = auto()


class ArbiterShutdownTaskResult(Enum):
    SUCCESS = auto()
    WARNING = auto()


class ArbiterCliCommand(Enum):
    H = auto()
    S = auto()
    K = auto()
    L = auto()
    Q = auto()

    def description(self):
        descriptions = {
            ArbiterCliCommand.H: "show commands",
            ArbiterCliCommand.S: "start service",
            ArbiterCliCommand.K: "stop service",
            ArbiterCliCommand.L: "display services",
            ArbiterCliCommand.Q: "quit arbiter",
        }
        return descriptions[self]

    def get_typer_text(self):
        return f"\t{self.name.lower()}\t{self.description()}"
