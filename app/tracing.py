"""OpenTelemetry distributed tracing setup.

Enabled via OTEL_ENABLED=true environment variable.
When disabled, all tracing calls are no-ops (zero overhead).
"""

import os
import logging

logger = logging.getLogger(__name__)

_tracer = None


def setup_tracing(service_name: str) -> bool:
    """Initialize OpenTelemetry tracing. Returns True if enabled."""
    global _tracer

    if os.environ.get("OTEL_ENABLED", "false").lower() != "true":
        logger.debug("OpenTelemetry tracing disabled (OTEL_ENABLED != true)")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Use OTLP exporter if configured, otherwise console
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        else:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer(service_name)
        logger.info("OpenTelemetry tracing enabled for %s", service_name)
        return True

    except ImportError:
        logger.warning("opentelemetry packages not installed — tracing disabled")
        return False
    except Exception as exc:
        logger.warning("Failed to setup tracing: %s", exc)
        return False


def get_tracer():
    """Get the global tracer (returns None if tracing is disabled)."""
    return _tracer
