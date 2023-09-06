from server.exceptions import BadRequest, NotAuthenticated, PermissionDenied, NotFound
from server.auth.constants import ErrorCode


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


class UserAlready(BadRequest):
    DETAIL = ErrorCode.USER_ALREADY


class AtLeastOneOwner(BadRequest):
    DETAIL = ErrorCode.PROTECT_OWNER


class NotAllowedUpdateRoleMaintainer(BadRequest):
    DETAIL = ErrorCode.NOT_ALLOWED_UPDATE_ROLE_MAINTAINER


class UserAlreadyConnected(BadRequest):
    DETAIL = ErrorCode.USER_ALREADY_CONNECTED


class EmailNotValid(BadRequest):
    DETAIL = ErrorCode.EMAIL_NOT_VALID


class EmailOrPasswordIncorrect(BadRequest):
    DETAIL = ErrorCode.EMAIL_OR_PASSWORD_INCORRECT
