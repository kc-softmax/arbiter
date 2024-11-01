from __future__ import annotations

import functools
import inspect
import asyncio
import os

from typing import Callable, AsyncIterator, AsyncGenerator

from opentelemetry import trace
from opentelemetry.trace import Tracer
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
    _tracer: Tracer = None
    
    def __init__(self, *args, **kwargs) -> None:
        self.headers: dict[str, str] = {}

    def _initialize_tracer(self):
        # service name은 singleton으로 선언되어야한다
        resource = Resource.create({SERVICE_NAME: "Arbiter"})
        trace.set_tracer_provider(TracerProvider(resource=resource))

        otlp_exporter = OTLPSpanExporter(endpoint=OTEL_SERVER_URL, insecure=True)
        processor = BatchSpanProcessor(otlp_exporter)  # Trace Exporter
        tracer_provider: TracerProvider = trace.get_tracer_provider()
        tracer_provider.add_span_processor(processor)

        # Tracer 인스턴스 생성
        return trace.get_tracer(__name__)

    def __new__(cls, name: str) -> TracerRepository:
        if name not in cls._instance:
            instance = super(TracerRepository, cls).__new__(cls)
            if cls._tracer is None:
                cls._tracer = instance._initialize_tracer()
            cls._instance[name] = instance
        return cls._instance[name]

    def _parse_headers(self, *args, **kwargs) -> None:
        for param in args:
            if hasattr(param, "headers"):
                _headers = dict(param.headers)
                if _headers.get("traceparent"):
                    self.headers["traceparent"] = _headers["traceparent"]
                break
        for value in kwargs.values():
            if hasattr(value, "headers"):
                _headers = dict(value.headers)
                if _headers.get("traceparent"):
                    self.headers["traceparent"] = _headers["traceparent"]
                break

    def __call__(self, traceparent: str = None) -> functools.Any:
        def decorator(func):
            return self.tracing(func, traceparent)
        return decorator

    def tracing(self, func: Callable[..., None], traceparent: str = None) -> Callable:

        span_name = func.__name__

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrappers(*args, **kwargs):
                if traceparent:
                    headers = TracerRepository.get_headers(traceparent)
                    context = extract(headers)
                else:
                    self._parse_headers(*args, **kwargs)
                    context = extract(self.headers)

                with self._tracer.start_as_current_span(span_name, context) as span:
                    span.add_event(func.__name__)
                    # for key, value in kwargs.items():
                    #     span.set_attribute(key, value)

                    # traceparent를 주입한다
                    inject(self.headers)

                    try:
                        res = await func(*args, **kwargs)
                        span.set_attribute("http.status", 200)
                    except Exception as err:
                        span.set_attribute("http.status", 500)
                        raise err
                    finally:
                        self._reset()
                return res
        else:
            @functools.wraps(func)
            def wrappers(*args, **kwargs):
                if traceparent:
                    headers = TracerRepository.get_headers(traceparent)
                    context = extract(headers)
                else:
                    self._parse_headers(*args, **kwargs)
                    context = extract(self.headers)

                with self._tracer.start_as_current_span(span_name, context) as span:
                    span.add_event(func.__name__)
                    # for key, value in kwargs.items():
                    #     span.set_attribute(key, value)

                    # traceparent를 주입한다
                    inject(self.headers)

                    try:
                        res = func(*args, **kwargs)
                        span.set_attribute("http.status", 200)
                    except Exception as err:
                        span.set_attribute("http.status", 500)
                        raise err
                    finally:
                        self._reset()
                return res
        return wrappers

    def _reset(self):
        self.headers.clear()

    @classmethod
    def get_headers(cls, tranceparent: str) -> dict[str, str]:
        return cls._instance[tranceparent].headers


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
#     second(x, y)


# @task(traceparent="task")
# def second(x: int, y: int):
#     print(x, y)
    

# first(1, 2)