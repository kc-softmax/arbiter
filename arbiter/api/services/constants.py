from enum import Enum


class ServicesRouterTag(str, Enum):
    MANAGE = "manage"
    MESSAGES = "messages"


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
