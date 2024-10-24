from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject, extract

OTEL_SERVER_URL = "http://localhost:4317"


class TracerSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TracerSingleton, cls).__new__(cls)
            cls._instance._initialize_tracer()
        return cls._instance

    def _initialize_tracer(self):
        resource = Resource.create({SERVICE_NAME: "trace_http_task"})
        trace.set_tracer_provider(TracerProvider(resource=resource))

        otlp_exporter = OTLPSpanExporter(endpoint=OTEL_SERVER_URL, insecure=True)
        processor = BatchSpanProcessor(otlp_exporter)  # Trace Exporter
        tracer_provider: TracerProvider = trace.get_tracer_provider()
        tracer_provider.add_span_processor(processor)

        # Tracer 인스턴스 생성
        self._tracer = trace.get_tracer(__name__)

    def get_tracer(self):
        return self._tracer
