import os
import sys
import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
# HTTP/Protobuf OTLP exporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # :contentReference[oaicite:0]{index=0}

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# ------------------------------------------------------------------------------
# 1) Basic logging: include trace & span IDs in your logs
# ------------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format=(
        "%(asctime)s %(name)s %(levelname)s "
        "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s"
    ),
)
logger = logging.getLogger("uvicorn.error")

# ------------------------------------------------------------------------------
# 2) TracerProvider & service resource
# ------------------------------------------------------------------------------
service_name = os.getenv("OTEL_SERVICE_NAME", "fastapi-service")
resource = Resource.create({SERVICE_NAME: service_name})
trace.set_tracer_provider(TracerProvider(resource=resource))

# ------------------------------------------------------------------------------
# 3) Debug: Console exporter to confirm spans locally
# ------------------------------------------------------------------------------
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

# ------------------------------------------------------------------------------
# 4) OTLP/HTTP exporter
#    Uses the HTTP endpoint at port 4318; OTEL_EXPORTER_OTLP_TRACES_ENDPOINT can override
# ------------------------------------------------------------------------------
http_endpoint = os.getenv(
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "http://localhost:4318/v1/traces"  # :contentReference[oaicite:1]{index=1}
)
http_exporter = OTLPSpanExporter(endpoint=http_endpoint)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(http_exporter)
)

# ------------------------------------------------------------------------------
# 5) FastAPI app + auto-instrumentation
# ------------------------------------------------------------------------------
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
LoggingInstrumentor().instrument(set_logging_format=True)

# ------------------------------------------------------------------------------
# 6) Your routes: each request will now generate a span + console log
# ------------------------------------------------------------------------------
@app.get("/hello")
async def hello():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("hello-span"):
        logger.info("Served /hello")
        return {"message": "Hello, FastAPI with OTLP/HTTP!"}

@app.get("/user/{user_id}")
async def get_user(user_id: int):
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("get-user-span"):
        logger.info(f"Fetching user {user_id}")
        return {"user_id": user_id, "name": "Alice"}

# ------------------------------------------------------------------------------
# 7) (Optional) Uvicorn entrypoint if you run `python -m app.main`
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # keep our basicConfig
    )
