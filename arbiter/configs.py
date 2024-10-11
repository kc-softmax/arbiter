from dataclasses import dataclass

@dataclass
class ArbiterConfig:
    name: str = "Danimoth"
    default_send_timeout: int = 5
    retry_attempts: int = 3
    retry_interval: float = 0.1
    log_level: str = "INFO"
    log_format: str = "%(name)% - %(level)s - %(message)s - %(datetime)s",

@dataclass
class ArbiterNodeConfig:
    system_timeout: int = 60
    preparation_timeout: int = 5
    initialization_timeout: int = 30
    disappearance_timeout: int = 10

@dataclass
class BrokerConfig:
    loading_timeout: int = 10
    max_clients: int = 1000

@dataclass
class RedisBrokerConfig(BrokerConfig):
    host: str = "localhost"
    port: int = 6379
    password: str = None
    db: int = 0

@dataclass
class NatsBrokerConfig(BrokerConfig):
    host: str = "localhost"
    port: int = 4222
    password: str = None
    max_reconnect_attempts: int = 5
    # TODO ADD MORE CONFIGS from nats.aio.connect