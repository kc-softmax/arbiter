from enum import IntEnum


class LiveConnectionEvent(IntEnum):
    VALIDATE = 100
    TIMEOUT = 102


class LiveSystemEvent(IntEnum):
    JOIN_GROUP = 50
    LEAVE_GROUP = 51
    REMOVE_GROUP = 52
    KICK_USER = 53
    ERROR = 99


class LiveConnectionState(IntEnum):
    PENDING = 201
    ACTIVATE = 202
    CLOSE = 203