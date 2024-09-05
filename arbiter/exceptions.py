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

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class TaskConnectionTimeout(TaskBaseError):
    """When connection timeout with other system resource"""

    def __init__(self, *args, **kwargs) -> None:
        self.message = kwargs.get("message", "system resource timeout when connect")
        self.timeout = kwargs.get("timeout", 5)
        super().__init__(f"{self.message} {self.timeout}s")


class TaskConnectionExceed(TaskBaseError):
    """When connection exceeded with other system resource"""

    def __init__(self, *args, **kwargs) -> None:
        self.message = kwargs.get("message", "Exceed number of maximum connection")
        self.number = kwargs.get("number", 5)
        super().__init__(f"{self.message} {self.number}")


class TaskExecutionTimeout(TaskBaseError):
    """When timeout in logic"""

    def __init__(self, *args, **kwargs) -> None:
        self.message = kwargs.get("message", "task timeout in running")
        self.timeout = kwargs.get("timeout", 5)
        super().__init__(f"{self.message} {self.timeout}s")


class TaskAlreadyRegistered(TaskBaseError):
    """When timeout in logic"""

    def __init__(self, *args, **kwargs) -> None:
        self.message = kwargs.get("message", "task already registered")
        self.task_name = kwargs.get("task_name")
        super().__init__(f"{self.message} {self.task_name}")
