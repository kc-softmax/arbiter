from ..exceptions import BadRequest, NotAuthenticated, PermissionDenied, NotFound
from .constants import ErrorCode


class AuthRequired(NotAuthenticated):
    DETAIL = ErrorCode.AUTHENTICATION_REQUIRED


class AuthorizationFailed(PermissionDenied):
    DETAIL = ErrorCode.AUTHORIZATION_FAILED


class InvalidToken(NotAuthenticated):
    DETAIL = ErrorCode.INVALID_TOKEN


class InvalidCredentials(NotAuthenticated):
    DETAIL = ErrorCode.INVALID_CREDENTIALS


class UserAlready(BadRequest):
    DETAIL = ErrorCode.USER_ALREADY


class RefreshTokenNotValid(NotAuthenticated):
    DETAIL = ErrorCode.REFRESH_TOKEN_NOT_VALID


class NotFoundUser(NotFound):
    DETAIL = ErrorCode.USER_NOT_FOUND
