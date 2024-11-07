from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable
from opentelemetry.trace import SpanKind


@dataclass
class TelemetryConfig:
    name: str
    otel_server_url: str = "http://localhost:4317"
    log_format: list[str] = field(default_factory=lambda :[
        "%(asctime)s %(levelname)s",
        "[%(name)s] [%(filename)s:%(lineno)d]",
        "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s"
        "resource.service.name=%(otelServiceName)s] - %(message)s"
    ])
    log_level: str = "INFO"
    set_logging_format: bool = True
    insecure: bool = True  # SSL true or false

@dataclass
class TraceConfig:
    request: bool
    responses: bool
    error: bool
    execution_times: bool
    span_kind: SpanKind = SpanKind.INTERNAL # visualize grafana
    callback: Callable = None

@dataclass
class ArbiterNodeConfig:
    system_timeout: int = 60
    preparation_timeout: int = 5
    initialization_timeout: int = 3
    materialization_timeout: int = 10
    disappearance_timeout: int = 10
    task_close_timeout: int = 5
    
    service_disappearance_timeout: int = 10
    service_health_check_interval: int = 1
    external_health_check_interval: float = 0.5 # MAX 1
    external_health_check_timeout: int = 10
    internal_health_check_timeout: int = 5
    
    gateway_refresh_interval: float = 1
    gateway_health_check_interval: float = 0.1
    internal_event_timeout: int = 1

@dataclass
class ArbiterConfig:
    name: str = "Danimoth"
    default_send_timeout: int = 5
    default_task_close_timeout: int = 5
    retry_attempts: int = 3
    retry_interval: float = 0.1
    log_level: str = "INFO"
    log_format: str = "%(name)% - %(level)s - %(message)s - %(datetime)s",
    loading_timeout: int = 10
    max_tasks: int = 1000

@dataclass
class RedisArbiterConfig(ArbiterConfig):
    host: str = "localhost"
    port: int = 6379
    password: str = None
    db: int = 0

@dataclass
class NatsArbiterConfig(ArbiterConfig):
    host: str = "localhost"
    port: int = 4222
    user: str = None
    password: str = None
    max_reconnect_attempts: int = 5
    # TODO ADD MORE CONFIGS from nats.aio.connect
