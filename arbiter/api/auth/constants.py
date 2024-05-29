from enum import Enum


class AuthRouterTag(str, Enum):
    TOKEN = "Token"
    USER = "Auth"


class ErrorCode(str, Enum):
    AUTHENTICATION_REQUIRED = "Authentication required."
    AUTHORIZATION_FAILED = "Authorization failed. User has no access."
    INVALID_TOKEN = "Invalid token."
    INVALID_CREDENTIALS = "Invalid credentials."
    USER_ALREADY_EXISTS = "User already exists"
    USER_NOT_FOUND = "User not found.",
    USER_NOT_FOUND_FOR_UPDATE = "There is no user you want to update"
    USER_NOT_FOUND_FOR_DELETE = "There are no users you want to delete"
    PROTECT_OWNER = "At least one OWNER permission must be maintained."
    NOT_ALLOWED_UPDATE_ROLE_MAINTAINER = "Maintainer can't update role"


class TOKEN_GENERATE_ALGORITHM(str, Enum):
    HS256 = "HS256"


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
