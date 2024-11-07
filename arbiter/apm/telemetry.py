from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.trace import Tracer, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

from arbiter.logger import ArbiterLogger
from arbiter.configs import TelemetryConfig


class TelemetryRepository:
    
    def __init__(self, telemetry_config: TelemetryConfig) -> None:
        self.telemetry_config = telemetry_config

    def get_tracer(self) -> Tracer:
        resource = Resource.create({SERVICE_NAME: self.telemetry_config.name})
        tracer_provider = TracerProvider(resource=resource)
        otlp_exporter = OTLPSpanExporter(
            endpoint=self.telemetry_config.otel_server_url,
            insecure=self.telemetry_config.insecure
        )
        processor = BatchSpanProcessor(otlp_exporter)  # Trace Exporter
        tracer_provider.add_span_processor(processor)

        return trace.get_tracer(self.telemetry_config.name, tracer_provider=tracer_provider)

    def get_logger(self) -> logging.Logger:
        # OpenTelemetry Logs
        formatter = " ".join(self.telemetry_config.log_format)
        arbiter_logger = ArbiterLogger(self.telemetry_config.name)
        logger_provider = LoggerProvider(
            resource=Resource.create(
                {
                    SERVICE_NAME: self.telemetry_config.name,
                    # "service.instance.id": "instance-12",
                }
            ),
        )
        otlp_exporter = OTLPLogExporter(
            endpoint=self.telemetry_config.otel_server_url,
            insecure=self.telemetry_config.insecure
        )
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))
        handler = LoggingHandler(
            level=self.telemetry_config.log_level,
            logger_provider=logger_provider
        )
        arbiter_logger.add_handler(handler)

        LoggingInstrumentor().instrument(
            set_logging_format=self.telemetry_config.set_logging_format,
            logging_format=formatter,
            log_level=self.telemetry_config.log_level
        )

        return arbiter_logger.logger
