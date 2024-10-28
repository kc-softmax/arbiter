from __future__ import annotations

import functools
import inspect
import asyncio

from typing import Callable, Any

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


class TracerRepositry:
    
    _instance = None
    _depth: dict[str, dict[str, str]] = {}
    
    def __init__(self, name: str) -> None:
        self.name = name

    def _initialize_tracer(self):
        # service name은 singleton으로 선언되어야한다
        resource = Resource.create({SERVICE_NAME: "Arbiter"})
        trace.set_tracer_provider(TracerProvider(resource=resource))

        otlp_exporter = OTLPSpanExporter(endpoint=OTEL_SERVER_URL, insecure=True)
        processor = BatchSpanProcessor(otlp_exporter)  # Trace Exporter
        tracer_provider: TracerProvider = trace.get_tracer_provider()
        tracer_provider.add_span_processor(processor)

        # Tracer 인스턴스 생성
        self._tracer = trace.get_tracer(__name__)

    def __new__(cls, *args, **kwargs) -> TracerRepositry:
        if cls._instance is None:
            cls._instance = super(TracerRepositry, cls).__new__(cls)
            cls._instance._initialize_tracer()
        return cls._instance

    def tracing(self, func: Callable[..., None] = None) -> Callable:

        if self.name and self.name not in self._depth:
            self._depth[self.name] = {}

        if self.name is None:
            self.name = func.__name__

        span_name = func.__name__

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrappers(*args, **kwargs):
                headers: dict[str, any] = self._depth[self.name] if self.name and self.name in self._depth else {}
                # traceparent를 추출한다
                context = extract(headers)
                with self._tracer.start_as_current_span(span_name, context) as span:
                    span.add_event(func.__name__)
                    for key, value in kwargs.items():
                        span.set_attribute(key, value)

                    # traceparent를 주입한다
                    inject(headers)

                    # inject 주입 후에 headers를 다시 갱신한다
                    if self.name in self._depth:
                        self._depth[self.name].update(headers)

                    try:
                        res = await func(*args, **kwargs)
                        span.set_attribute("http.status", 200)
                    except Exception as err:
                        span.set_attribute("http.status", 500)
                        raise err
                return res
        else:
            @functools.wraps(func)
            def wrappers(*args, **kwargs):
                headers: dict[str, any] = self._depth[self.name] if self.name and self.name in self._depth else {}
                context = extract(headers)
                with self._tracer.start_as_current_span(span_name, context) as span:
                    span.add_event(func.__name__)
                    for key, value in kwargs.items():
                        span.set_attribute(key, value)

                    # traceparent를 주입한다
                    inject(headers)

                    # inject 주입 후에 headers를 다시 갱신한다
                    if self.name in self._depth:
                        self._depth[self.name].update(headers)

                    try:
                        res = func(*args, **kwargs)
                        span.set_attribute("http.status", 200)
                    except Exception as err:
                        span.set_attribute("http.status", 500)
                        raise err
                return res
        return wrappers


class SimpleTelemetry:

    @staticmethod
    def register_trace(name: str = None):
        task = TracerRepositry(name=name)
        def decorator(func):
            return task.tracing(func)
        return decorator


# simple_telemetry = SimpleTelemetry()
# @simple_telemetry.register_trace(name="arbiter")
# def second(x: int, y: int):
#     pass


# @simple_telemetry.register_trace(name="arbiter")
# async def first():
#     second(x=1, y=2)

# if __name__ == '__main__':
#     asyncio.run(first())
