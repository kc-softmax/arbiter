class ArbiterDecodeError(Exception):
    """Raised when an arbiter fails to decode a message from a worker."""
    pass

class AribterEncodeError(Exception):
    """Raised when an arbiter fails to encode a message to a worker."""
    pass

class ArbiterTaskAlreadyExistsError(Exception):
    """Raised when a task is already registered with the arbiter."""
    def __init__(self, message="The task is already registered with the arbiter."):
        super().__init__(message)

class ArbiterAlreadyRegistedServiceMetaError(Exception):
    """Raised when the arbiter has already registered a service meta."""
    def __init__(self, message="The arbiter has already registered a service meta."):
        super().__init__(message)

class ArbiterInconsistentServiceModelError(Exception):
    """Raised when the arbiter has inconsistent service."""
    def __init__(self, message="The arbiter has inconsistent service model."):
        super().__init__(message)
        
class ArbiterServiceHealthCheckError(Exception):
    """Raised when the arbiter fails to health check a service."""
    def __init__(self, message="The arbiter fails to health check a service."):
        super().__init__(message)
        
class ArbiterServerNodeFaileToStartError(Exception):
    """Raised when the arbiter server node fails to start."""
    def __init__(self, message="The arbiter server node fails to start."):
        super().__init__(message)

class ArbiterServiceNodeFaileToStartError(Exception):
    """Raised when the arbiter service node fails to start."""
    def __init__(self, message="The arbiter service node fails to start."):
        super().__init__(message)