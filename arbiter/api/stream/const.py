from enum import IntEnum


class StreamSystemEvent(IntEnum):
    VALIDATE = 100
    TIMEOUT = 102
    SUBSCRIBE = 103
    UNSUBSCRIBE = 104
    ERROR = 105
