# https://datatracker.ietf.org/doc/html/rfc6455#section-7.4.1
# TODO: 4000대로 변경해야함
class AuthorizationFailedClose:
    CODE = 3000
    REASON = "invalid token"


class AlreadyConnected:
    CODE = 3100
    REASON = "already connected"


class UserDisconnected:
    CODE = 3101
    REASON = "user disconnected"


class AlreadyJoinedRoom:
    CODE = 3500
    REASON = "already joined room"


class AlreadyLeftRoom:
    CODE = 3501
    REASON = "already left room"


class RoomDoesNotExist:
    CODE = 3600
    REASON = "room does not exist"


class RoomIsFull:
    CODE = 3700
    REASON = "room is full"


class RoomIsExist:
    CODE = 3701
    REASON = "room is exist"


class MessageIsNotExists:
    CODE = 3800
    REASON = "message is not exists"


class UnCheckedError:
    CODE = 9999
    REASON = "Chat Server Error"