import functools
import inspect

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


class TracerSingleton:
    _instance = None
    _depth: dict[str, dict[str, any]] = {}

    def __new__(cls, name: str = None, *, func: Callable[..., Any] = None):
        if func is None:
            if name and not cls._depth.get(name):
                cls._depth[name] = {}
            return lambda func: cls(name=name, func=func)

        if cls._instance is None:
            cls._instance = super(TracerSingleton, cls).__new__(cls)
            cls._instance._initialize_tracer()

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrappers(*args, **kwargs):
                headers: dict[str, any] = cls._depth[name] if name and cls._depth.get(name) else {}
                context = extract(headers)
                with cls._instance._tracer.start_as_current_span(name, context) as span:
                    span.add_event(func.__name__)
                    for key, value in kwargs.items():
                        span.set_attribute(key, value)
                    inject(headers)
                    # inject 주입 후에 headers를 다시 갱신한다
                    cls._depth[name].update(headers)
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
                headers: dict[str, any] = cls._depth[name] if name and cls._depth.get(name) else {}
                context = extract(headers)
                with cls._instance._tracer.start_as_current_span(name, context) as span:
                    span.add_event(func.__name__)
                    for key, value in kwargs.items():
                        span.set_attribute(key, value)
                    inject(headers)
                    # inject 주입 후에 headers를 다시 갱신한다
                    cls._depth[name].update(headers)
                    try:
                        res = func(*args, **kwargs)
                        span.set_attribute("http.status", 200)
                    except Exception as err:
                        span.set_attribute("http.status", 500)
                        raise err
                return res
        return wrappers

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


# import asyncio


# @TracerSingleton(name="hello")
# def hello(x: int, y: int):
#     pass


# @TracerSingleton(name="hello")
# async def main():
#     hello(1, 2)

# if __name__ == '__main__':
#     asyncio.run(main())