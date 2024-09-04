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


### Exception Group ###
class BaseError(Exception):
    """Top Level Error"""


class RetryExceed(BaseError):
    """When exceed number of retry"""


class SystemBaseError(BaseError):
    """System Node Level Error"""


class ServiceBaseError(BaseError):
    """Worker Node Level Error"""


class TaskBaseError(BaseError):
    """Task Node Level Error"""


class ConnectionTimeout(TaskBaseError):
    """When connection timeout with other system resource"""

    def __init__(self, message: str = "system resource timeout when connect", timeout: int = 5) -> None:
        self.message = message
        self.timeout = timeout
        super().__init__(f"{self.message}, {self.timeout}s")


class ConnectionExceed(TaskBaseError):
    """When connection exceeded with other system resource"""

    def __init__(self, message: str = "Exceed number of maximum connection", number: int = 5) -> None:
        self.message = message
        self.number = number
        super().__init__(f"{self.message}, {self.number}")


class TaskTimeout(TaskBaseError):
    """When timeout in logic"""

    def __init__(self, message: str = "task timeout in running", timeout: int = 5) -> None:
        self.message = message
        self.timeout = timeout
        super().__init__(f"{self.message}, {self.timeout}s")
