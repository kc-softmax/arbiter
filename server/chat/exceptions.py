class AuthorizationFailedClose:
    CODE = 3000
    REASON = "invalid token"


class AlreadyConnected:
    CODE = 3100
    REASON = "already connected"


class AlreadyJoinedRoom:
    CODE = 3500
    REASON = "already joined room"


class RoomDoesNotExist:
    CODE = 3600
    REASON = "room does not exist"


class RoomIsFull:
    CODE = 3700
    REASON = "room is full"


class RoomIsExist:
    CODE = 3800
    REASON = "room is exist"
