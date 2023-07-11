from enum import StrEnum


class ErrorCode(StrEnum):
    AUTHENTICATION_REQUIRED = "Authentication required."
    AUTHORIZATION_FAILED = "Authorization failed. User has no access."
    INVALID_TOKEN = "Invalid token."
    INVALID_CREDENTIALS = "Invalid credentials."
    USER_ALREADY = "User already exists"
    REFRESH_TOKEN_NOT_VALID = "Refresh token is not valid."
    USER_NOT_FOUND = "User not found."


class TOKEN_GENERATE_ALGORITHM(StrEnum):
    HS256 = "HS256"


ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
