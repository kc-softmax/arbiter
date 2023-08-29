from enum import StrEnum


class ErrorCode(StrEnum):
    AUTHENTICATION_REQUIRED = "Authentication required."
    AUTHORIZATION_FAILED = "Authorization failed. User has no access."
    INVALID_TOKEN = "Invalid token."
    INVALID_CREDENTIALS = "Invalid credentials."
    USER_ALREADY = "User already exists"
    USER_NOT_FOUND = "User not found.",
    USER_NOT_FOUND_FOR_UPDATE = "There is no user you want to update"
    USER_NOT_FOUND_FOR_DELETE = "There are no users you want to delete"
    PROTECT_OWNER = "At least one OWNER permission must be maintained."
    NOT_ALLOWED_UPDATE_ROLE_MAINTAINER = "Maintainer can't update role"
    USER_ALREADY_CONNECTED = "User already connected"


class TOKEN_GENERATE_ALGORITHM(StrEnum):
    HS256 = "HS256"


ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
