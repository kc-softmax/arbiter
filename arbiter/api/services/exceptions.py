from arbiter.api.exceptions import BadRequest, NotAuthenticated, PermissionDenied, NotFound
from arbiter.api.auth.constants import ErrorCode


class ServiceNotFound(NotFound):
    DETAIL = "Service not found"
