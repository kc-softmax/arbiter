from __future__ import annotations

import logging

from opentelemetry import trace, metrics
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
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider, Meter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, MetricExporter

from arbiter.logger import ArbiterLogger


OTEL_SERVER_URL = "http://localhost:4317"


class TelemetryRepository:
    
    def __init__(self, name: str) -> None:
        self.name = name
        self.headers: dict[str, str] = {}

    def get_tracer(self) -> Tracer:
        resource = Resource.create({SERVICE_NAME: self.name})
        tracer_provider = TracerProvider(resource=resource)
        otlp_exporter = OTLPSpanExporter(endpoint=OTEL_SERVER_URL, insecure=True)
        processor = BatchSpanProcessor(otlp_exporter)  # Trace Exporter
        tracer_provider.add_span_processor(processor)

        return trace.get_tracer(self.name, tracer_provider=tracer_provider)

    def get_logger(self, level: int = logging.INFO) -> logging.Logger:
        # OpenTelemetry Logs
        formatter = " ".join([
            "%(asctime)s %(levelname)s",
            "[%(name)s] [%(filename)s:%(lineno)d]",
            "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s"
            "resource.service.name=%(otelServiceName)s] - %(message)s"
        ])
        arbiter_logger = ArbiterLogger(self.name)
        logger_provider = LoggerProvider(
            resource=Resource.create(
                {
                    SERVICE_NAME: self.name,
                    # "service.instance.id": "instance-12",
                }
            ),
        )
        otlp_exporter = OTLPLogExporter(endpoint=OTEL_SERVER_URL, insecure=True)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))
        handler = LoggingHandler(level=level, logger_provider=logger_provider)
        arbiter_logger.add_handler(handler)

        LoggingInstrumentor().instrument(
            set_logging_format=True,
            logging_format=formatter,
            log_level=level
        )

        return arbiter_logger.logger

    def get_meter(self) -> Meter:
        otlp_metric_exporter = OTLPMetricExporter(OTEL_SERVER_URL, insecure=False)
        # metric_exporter = MetricExporter()
        metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
        meter_provider = MeterProvider(
            resource=Resource.create(
                {
                    SERVICE_NAME: self.name,
                    # "service.instance.id": "instance-12",
                }
            ),
            metric_readers=[metric_reader]
        )
        return metrics.get_meter(name=self.name, meter_provider=meter_provider)
