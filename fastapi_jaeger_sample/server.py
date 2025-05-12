#!/usr/bin/env python3


import os
import sys
import logging
from concurrent import futures

import grpc

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.instrumentation.logging import LoggingInstrumentor

import hello_pb2
import hello_pb2_grpc

# ------------------------------------------------------------------------------
# 1) Auto-instrument the gRPC server so incoming calls become spans
# ------------------------------------------------------------------------------
GrpcInstrumentorServer().instrument()

# ------------------------------------------------------------------------------
# 2) Auto-instrument Python logging so each LogRecord gets trace/span IDs
# ------------------------------------------------------------------------------
LoggingInstrumentor().instrument(set_logging_format=True)

# ------------------------------------------------------------------------------
# 3) Now configure your log format (must include otelTraceID & otelSpanID)
# ------------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format=(
        "%(asctime)s %(name)s %(levelname)s "
        "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s"
    ),
)
logger = logging.getLogger("grpc-server")

# ------------------------------------------------------------------------------
# 4) Set up the TracerProvider with your service name
# ------------------------------------------------------------------------------
service_name = os.getenv("OTEL_SERVICE_NAME", "grpc-service")
resource = Resource.create({SERVICE_NAME: service_name})
trace.set_tracer_provider(TracerProvider(resource=resource))

# ------------------------------------------------------------------------------
# 5) Attach a ConsoleSpanExporter for local debugging
# ------------------------------------------------------------------------------
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

# ------------------------------------------------------------------------------
# 6) Attach the OTLP/gRPC exporter (to Jaeger on localhost:4317)
# ------------------------------------------------------------------------------
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# ------------------------------------------------------------------------------
# 7) Implement your gRPC service with manual spans + logging
# ------------------------------------------------------------------------------
class GreeterServicer(hello_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("SayHello-span"):
            logger.info(f"Handling SayHello request: name={request.name}")
            return hello_pb2.HelloReply(message=f"Hello, {request.name}!")

# ------------------------------------------------------------------------------
# 8) Start the gRPC server
# ------------------------------------------------------------------------------
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    hello_pb2_grpc.add_GreeterServicer_to_server(GreeterServicer(), server)
    port = os.getenv("GRPC_PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    logger.info(f"Starting gRPC server on port {port}...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

#python -m grpc_tools.protoc -Iproto --python_out=. --grpc_python_out=. proto/hello.proto