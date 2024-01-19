from enum import IntEnum


class StreamSystemEvent(IntEnum):
    VALIDATE = 100
    TIMEOUT = 102
    FORCE_CLOSE = 103
    ERROR = 104
