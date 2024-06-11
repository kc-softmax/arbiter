from enum import IntEnum


class ArbiterMessageType(IntEnum):
    # General messages
    PING = 0
    PONG = 1

    SHUTDOWN = 2
    # Arbiter messages
    ARBITER_SERVICE_REGISTER = 10
    ARBITER_SERVICE_REGISTER_ACK = 11
    ARBITER_SERVICE_UNREGISTER = 12
    ARBITER_SERVICE_UNREGISTER_ACK = 13
    ARBITER_SERVICE_STOP = 14
    ARBITER_SERVICE_STOP_ACK = 15

    # Worker messages
    WORKER_REGISTER = 20
    WORKER_REGISTER_ACK = 21
    WORKER_UNREGISTER = 22
    WORKER_UNREGISTER_ACK = 23
    WORKER_GET = 24
    WORKER_GET_ACK = 25

    # Task messages
    TASK_SUBMIT = 30
    TASK_SUBMIT_ACK = 31
    TASK_CANCEL = 32
    TASK_CANCEL_ACK = 33
    TASK_GET = 34
    TASK_GET_ACK = 35

    # Result messages
    RESULT_SUBMIT = 40
    RESULT_SUBMIT_ACK = 41
    RESULT_GET = 42
    RESULT_GET_ACK = 43

    # Error messages
    ERROR = 50

    # Internal messages
    INTERNAL = 60
