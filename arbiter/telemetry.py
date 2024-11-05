from __future__ import annotations

import functools
import inspect
import asyncio
import os

from typing import Any, Callable, AsyncIterator, AsyncGenerator

from opentelemetry import trace
from opentelemetry.trace import Tracer, StatusCode
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject, extract


OTEL_SERVER_URL = "http://localhost:4317"


class TracerRepository:
    
    _instance: dict[str, TracerRepository] = {}
    tracer: Tracer = None
    
    def __new__(cls, name: str) -> TracerRepository:
        if name not in cls._instance:
            instance = super(TracerRepository, cls).__new__(cls)
            if cls.tracer is None:
                cls.tracer = instance._initialize_tracer(name)
            cls._instance[name] = instance
        return cls._instance[name]
    
    def __init__(self, name: str) -> None:
        self.name = name
        self.headers: dict[str, str] = {}

    def _initialize_tracer(self, name):
        # service name은 singleton으로 선언되어야한다
        resource = Resource.create({SERVICE_NAME: name})
        trace.set_tracer_provider(TracerProvider(resource=resource))

        otlp_exporter = OTLPSpanExporter(endpoint=OTEL_SERVER_URL, insecure=True)
        processor = BatchSpanProcessor(otlp_exporter)  # Trace Exporter
        tracer_provider: TracerProvider = trace.get_tracer_provider()
        tracer_provider.add_span_processor(processor)

        # Tracer 인스턴스 생성
        return trace.get_tracer(__name__)

# node = TracerRepository(name="node")

# @node()
# def first(x: int, y: int):
#     second(x, y)


# @node()
# def second(x: int, y: int):
#     print(x, y)
    

# first(1, 2)

# node = TracerRepository(name="node")
# task = TracerRepository(name="task")

# @node()
# def first(x: int, y: int):
#     second(x=x, y=y)


# @task(traceparent="node")
# def second(x: int, y: int):
#     print(x, y)
    

# first(x=1, y=2)