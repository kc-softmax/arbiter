
class ArbiterTimeOutError(Exception):
    """Raised when an arbiter times out waiting for a response from a worker."""
    pass

class ArbiterDecodeError(Exception):
    """Raised when an arbiter fails to decode a message from a worker."""
    pass

class ArbiterTaskAlreadyExistsError(Exception):
    """Raised when a task is already registered with the arbiter."""
    def __init__(self, message="The task is already registered with the arbiter."):
        super().__init__(message)

class ArbiterTooManyWebServiceError(Exception):
    """Raised when the arbiter has too many web services."""
    def __init__(self, message="The arbiter has too many web services."):
        super().__init__(message)

class ArbiterNoWebServiceError(Exception):
    """Raised when the arbiter has no web services."""
    def __init__(self, message="The arbiter has no web services."):
        super().__init__(message)


class ArbiterAlreadyRegistedServiceMetaError(Exception):
    """Raised when the arbiter has already registered a service meta."""
    def __init__(self, message="The arbiter has already registered a service meta."):
        super().__init__(message)

class ArbiterInconsistentServiceMetaError(Exception):
    """Raised when the arbiter has inconsistent service."""
    def __init__(self, message="The arbiter has inconsistent service meta."):
        super().__init__(message)