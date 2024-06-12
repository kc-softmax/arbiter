from arbiter.service import AbstractService
from arbiter.broker import RedisBroker


class RedisService(AbstractService[RedisBroker]):

    def __init__(self, frequency: float = 1.0):
        super().__init__(RedisBroker, frequency)
