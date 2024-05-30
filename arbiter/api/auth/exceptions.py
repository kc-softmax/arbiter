from arbiter.api.exceptions import BadRequest, NotAuthenticated, PermissionDenied, NotFound
from arbiter.api.auth.constants import ErrorCode


class AuthorizationFailed(PermissionDenied):
    DETAIL = ErrorCode.AUTHORIZATION_FAILED


class AuthRequired(NotAuthenticated):
    DETAIL = ErrorCode.AUTHENTICATION_REQUIRED


class InvalidToken(NotAuthenticated):
    DETAIL = ErrorCode.INVALID_TOKEN


class InvalidCredentials(NotAuthenticated):
    DETAIL = ErrorCode.INVALID_CREDENTIALS


class NotFoundUser(NotFound):
    DETAIL = ErrorCode.USER_NOT_FOUND


class NotFoundUserForDelete(NotFound):
    DETAIL = ErrorCode.USER_NOT_FOUND_FOR_DELETE


class NotFoundUserForUpdate(NotFound):
    DETAIL = ErrorCode.USER_NOT_FOUND_FOR_UPDATE


class UserAlreadyExists(BadRequest):
    DETAIL = ErrorCode.USER_ALREADY_EXISTS


class AtLeastOneOwner(BadRequest):
    DETAIL = ErrorCode.PROTECT_OWNER


class NotAllowedUpdateRoleMaintainer(BadRequest):
    DETAIL = ErrorCode.NOT_ALLOWED_UPDATE_ROLE_MAINTAINER
