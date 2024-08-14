
class ArbiterTimeOutError(Exception):
    """Raised when an arbiter times out waiting for a response from a worker."""
    pass

class ArbiterDecodeError(Exception):
    """Raised when an arbiter fails to decode a message from a worker."""
    pass