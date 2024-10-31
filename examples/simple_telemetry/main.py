from __future__ import annotations

import functools
import inspect
import asyncio
import os

from typing import Callable, AsyncIterator, AsyncGenerator

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject, extract
from starlette.requests import Request

OTEL_SERVER_URL = "http://localhost:4317"


class TracerRepositry:
    
    _instance = None
    _depth: dict[str, dict[str, str]] = {}
    
    def __init__(self, name: str) -> None:
        self.name = name

    def _initialize_tracer(self):
        # service name은 singleton으로 선언되어야한다
        # resource = Resource.create({SERVICE_NAME: "Arbiter"})
        resource = Resource.create({SERVICE_NAME: str(os.getpid())})
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

    def _reset(self):
        self._depth[self.name].clear()

    def _parse_headers(self, *args, **kwargs) -> dict[str, str]:
        for param in args:
            if hasattr(param, "headers"):
                _headers = dict(param.headers)
                if _headers.get("traceparent"):
                    self._depth[self.name] = {"traceparent": _headers["traceparent"]}
                break
        for value in kwargs.values():
            if hasattr(value, "headers"):
                _headers = dict(value.headers)
                if _headers.get("traceparent"):
                    self._depth[self.name] = {"traceparent": _headers["traceparent"]}
                break

        if kwargs.get("headers"):
            headers = kwargs.get("headers")
        else:
            headers: dict[str, any] = self._depth[self.name]
        return headers

    def tracing(self, func: Callable[..., None] = None) -> Callable:

        if self.name is None:
            self.name = func.__name__

        if self.name and self.name not in self._depth:
            self._depth[self.name] = {}

        span_name = func.__name__

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrappers(*args, **kwargs):
                # 외부 서비스로부터 header가 주입되었다
                headers = self._parse_headers(*args, **kwargs)

                # traceparent를 추출한다
                context = extract(headers)
                with self._tracer.start_as_current_span(span_name, context) as span:
                    span.add_event(func.__name__)
                    # for key, value in kwargs.items():
                    #     span.set_attribute(key, value)

                    # traceparent를 주입한다
                    inject(headers)

                    # inject 주입 후에 headers를 다시 갱신한다
                    self._depth[self.name].update(headers)

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
                # 외부 서비스로부터 header가 주입되었다
                headers = self._parse_headers(*args, **kwargs)

                # traceparent를 추출한다
                context = extract(headers)
                with self._tracer.start_as_current_span(span_name, context) as span:
                    span.add_event(func.__name__)
                    # for key, value in kwargs.items():
                    #     span.set_attribute(key, value)

                    # traceparent를 주입한다
                    inject(headers)

                    # inject 주입 후에 headers를 다시 갱신한다
                    self._depth[self.name].update(headers)

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

    def get_headers(self) -> str:
        return self._depth.get(self.name, {})


class SimpleTelemetry:

    def __init__(self):
        self.tracer: TracerRepositry = None

    def register_trace(self, name: str = None):
        self.tracer = TracerRepositry(name=name)
        def decorator(func):
            return self.tracer.tracing(func)
        return decorator

    def get_headers(self) -> dict[str, str]:
        return self.tracer.get_headers()


# import requests
# import nats
# simple_telemetry = SimpleTelemetry()
# @simple_telemetry.register_trace(name="arbiter")
# async def second(x: int, y: int):
#     headers = simple_telemetry.get_headers()
#     # res = requests.get("/", headers=headers)
#     # nat = await nats.connect()
#     # nat.publish("TEST", headers=headers)
#     pass


# @simple_telemetry.register_trace(name="arbiter")
# async def first():
#     await second(x=1, y=2)

# if __name__ == '__main__':
#     asyncio.run(first())
