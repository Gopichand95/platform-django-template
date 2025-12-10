Observability and Structured Logging
====================================

.. index:: logging, observability, tracing, metrics, opentelemetry, structlog

This guide explains how to implement production-ready observability in your Django application using structured logging and OpenTelemetry. You'll learn to send logs, traces, and metrics to backends like CloudWatch, Datadog, or any OTLP-compatible service.

Overview
--------

Modern production systems need more than ``print()`` statements and plain text log files. When your application runs across multiple containers, handles thousands of requests per second, and integrates with external services, you need **observability**—the ability to understand what's happening inside your system by examining its outputs.

Observability rests on three pillars:

**Logs**: Discrete events that record what happened. "User 123 logged in." "Payment processing failed."

**Traces**: The journey of a request through your system. A single API call might touch Django, Celery, Redis, PostgreSQL, and an external service. Traces connect these hops into a single story.

**Metrics**: Aggregated measurements over time. Request latency percentiles, error rates, queue depths.

This guide focuses primarily on logs and traces. The template already includes Sentry for error tracking, which covers the most critical observability need. This guide extends your capabilities for deeper debugging, performance analysis, and compliance requirements.

The Problem with Plain Text Logs
--------------------------------

The default Django logging configuration outputs plain text:

.. code-block:: text

    INFO 2024-01-15 14:32:01 views 12345 67890 User logged in successfully

This works for local development but creates problems in production:

**Hard to parse**: Log aggregators like CloudWatch or Datadog work best with structured data. Parsing ``%(module)s %(process)d %(thread)d`` with regex is fragile.

**No context**: Which user? Which request? Which server? You need to manually add this information to every log call.

**No correlation**: When a request spans multiple services or background tasks, there's no way to connect related log entries.

**Inconsistent format**: Different libraries log in different formats. Django, Celery, and your code all produce slightly different output.

Structured logging solves these problems by outputting logs as JSON with consistent fields. Combined with OpenTelemetry, you get automatic correlation across your entire request lifecycle.

Structured Logging with structlog
---------------------------------

`structlog <https://www.structlog.org/>`_ is a Python logging library that produces structured log output while maintaining a pleasant development experience. It integrates cleanly with Django's logging infrastructure and OpenTelemetry.

Installation
^^^^^^^^^^^^

Add structlog to your requirements:

.. code-block:: text

    # requirements/base.txt
    structlog==24.4.0

Configuring Django Logging
^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace the default logging configuration in ``config/settings/base.py``:

.. code-block:: python

    # config/settings/base.py
    import structlog

    # Shared processors for all environments
    STRUCTLOG_SHARED_PROCESSORS = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog
    structlog.configure(
        processors=STRUCTLOG_SHARED_PROCESSORS
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain_console": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=True),
                "foreign_pre_chain": STRUCTLOG_SHARED_PROCESSORS,
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": STRUCTLOG_SHARED_PROCESSORS,
            },
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "plain_console",  # Pretty output for development
            },
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {
            "django.db.backends": {
                "level": "WARNING",  # Reduce SQL noise
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

This configuration:

1. Uses pretty-printed colored output in development (``plain_console``)
2. Defines a JSON formatter for production (``json``)
3. Captures context variables automatically via ``merge_contextvars``
4. Adds timestamps, log levels, and logger names consistently

Production Configuration
^^^^^^^^^^^^^^^^^^^^^^^^

Override the formatter in production to output JSON:

.. code-block:: python

    # config/settings/production.py
    from .base import LOGGING

    # Switch to JSON output for log aggregators
    LOGGING["handlers"]["console"]["formatter"] = "json"

Using structlog in Your Code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get a logger and use it like standard logging, but with structured context:

.. code-block:: python

    # {project_slug}/orders/services.py
    import structlog

    logger = structlog.get_logger(__name__)

    class OrderService:
        @classmethod
        def place_order(cls, user, items):
            # Add context that appears in all subsequent logs
            log = logger.bind(user_id=user.id, item_count=len(items))

            log.info("placing_order")

            try:
                order = Order.objects.create(user=user)
                for item in items:
                    OrderItem.objects.create(order=order, **item)

                log.info("order_placed", order_id=order.id, total=order.total)
                return order

            except Exception as e:
                log.exception("order_placement_failed", error=str(e))
                raise

In development, this outputs:

.. code-block:: text

    2024-01-15 14:32:01 [info     ] placing_order                  user_id=123 item_count=3
    2024-01-15 14:32:01 [info     ] order_placed                   user_id=123 item_count=3 order_id=456 total=99.99

In production (JSON):

.. code-block:: json

    {"event": "placing_order", "user_id": 123, "item_count": 3, "level": "info", "timestamp": "2024-01-15T14:32:01.123456Z"}
    {"event": "order_placed", "user_id": 123, "item_count": 3, "order_id": 456, "total": 99.99, "level": "info", "timestamp": "2024-01-15T14:32:01.234567Z"}

Request Context Middleware
^^^^^^^^^^^^^^^^^^^^^^^^^^

Add request information automatically to all logs within a request:

.. code-block:: python

    # {project_slug}/core/middleware.py
    import uuid
    import structlog

    class RequestContextMiddleware:
        """Add request context to all logs within a request."""

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            # Generate or extract request ID
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

            # Clear any previous context and set new values
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                request_id=request_id,
                path=request.path,
                method=request.method,
            )

            # Add user info after authentication
            if hasattr(request, "user") and request.user.is_authenticated:
                structlog.contextvars.bind_contextvars(user_id=request.user.id)

            response = self.get_response(request)

            # Optionally add request ID to response headers
            response["X-Request-ID"] = request_id

            return response

Register the middleware in settings:

.. code-block:: python

    # config/settings/base.py
    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        # ... other middleware ...
        "{project_slug}.core.middleware.RequestContextMiddleware",  # Add after auth
        # ... rest of middleware ...
    ]

Now every log within a request automatically includes ``request_id``, ``path``, ``method``, and ``user_id``.

OpenTelemetry Integration
-------------------------

OpenTelemetry (OTEL) is the industry standard for distributed tracing and metrics. It provides automatic instrumentation for Django, Celery, Redis, and PostgreSQL, plus the ability to create custom spans for your business logic.

Installation
^^^^^^^^^^^^

Add OpenTelemetry packages to your requirements:

.. code-block:: text

    # requirements/base.txt
    opentelemetry-api==1.29.0
    opentelemetry-sdk==1.29.0
    opentelemetry-instrumentation-django==0.50b0
    opentelemetry-instrumentation-psycopg2==0.50b0
    opentelemetry-instrumentation-redis==0.50b0
    opentelemetry-instrumentation-celery==0.50b0
    opentelemetry-exporter-otlp==1.29.0

Basic Configuration
^^^^^^^^^^^^^^^^^^^

Initialize OpenTelemetry in your WSGI or ASGI entry point:

.. code-block:: python

    # config/otel.py
    import os
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    def configure_opentelemetry():
        """Configure OpenTelemetry tracing."""

        # Skip if not configured
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not otlp_endpoint:
            return

        service_name = os.environ.get("OTEL_SERVICE_NAME", "django-app")

        # Create resource with service name
        resource = Resource.create({SERVICE_NAME: service_name})

        # Create and set tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        trace.set_tracer_provider(provider)

        # Auto-instrument libraries
        DjangoInstrumentor().instrument()
        Psycopg2Instrumentor().instrument()
        RedisInstrumentor().instrument()

Call this during application startup:

.. code-block:: python

    # config/wsgi.py
    import os
    from django.core.wsgi import get_wsgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

    # Initialize OpenTelemetry before Django
    from config.otel import configure_opentelemetry
    configure_opentelemetry()

    application = get_wsgi_application()

For ASGI (if using ``use_async=y``):

.. code-block:: python

    # config/asgi.py
    import os
    from django.core.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

    # Initialize OpenTelemetry before Django
    from config.otel import configure_opentelemetry
    configure_opentelemetry()

    application = get_asgi_application()

Celery Instrumentation
^^^^^^^^^^^^^^^^^^^^^^

For Celery, add instrumentation in the Celery app configuration:

.. code-block:: python

    # config/celery_app.py
    import os
    from celery import Celery
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

    app = Celery("{project_slug}")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()

    # Instrument Celery
    CeleryInstrumentor().instrument()

Custom Spans
^^^^^^^^^^^^

For important business operations, create custom spans:

.. code-block:: python

    # {project_slug}/orders/services.py
    from opentelemetry import trace
    import structlog

    logger = structlog.get_logger(__name__)
    tracer = trace.get_tracer(__name__)

    class OrderService:
        @classmethod
        def place_order(cls, user, items):
            with tracer.start_as_current_span("place_order") as span:
                span.set_attribute("user.id", user.id)
                span.set_attribute("order.item_count", len(items))

                log = logger.bind(user_id=user.id, item_count=len(items))
                log.info("placing_order")

                try:
                    with tracer.start_as_current_span("create_order_record"):
                        order = Order.objects.create(user=user)

                    with tracer.start_as_current_span("create_order_items"):
                        for item in items:
                            OrderItem.objects.create(order=order, **item)

                    span.set_attribute("order.id", order.id)
                    span.set_attribute("order.total", float(order.total))
                    log.info("order_placed", order_id=order.id)
                    return order

                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    log.exception("order_placement_failed")
                    raise

Connecting Logs to Traces
^^^^^^^^^^^^^^^^^^^^^^^^^

Add trace context to your structlog configuration so logs include trace and span IDs:

.. code-block:: python

    # config/settings/base.py
    from opentelemetry import trace

    def add_trace_context(logger, method_name, event_dict):
        """Add OpenTelemetry trace context to log records."""
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
        return event_dict

    STRUCTLOG_SHARED_PROCESSORS = [
        structlog.contextvars.merge_contextvars,
        add_trace_context,  # Add this processor
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

Now your JSON logs include ``trace_id`` and ``span_id``, allowing you to correlate logs with traces in your observability platform.

Exporting to Backends
---------------------

OpenTelemetry uses the OTLP (OpenTelemetry Protocol) to export telemetry data. Most observability platforms support OTLP directly or via the OpenTelemetry Collector.

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

Configure exporters via environment variables:

.. code-block:: bash

    # .env or environment configuration
    OTEL_SERVICE_NAME=myproject-api
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
    OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer <token>

Local Development with Jaeger
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For local development, run Jaeger to visualize traces:

.. code-block:: yaml

    # docker-compose.local.yml (add to existing file)
    services:
      jaeger:
        image: jaegertracing/all-in-one:1.53
        ports:
          - "16686:16686"  # UI
          - "4317:4317"    # OTLP gRPC
          - "4318:4318"    # OTLP HTTP
        environment:
          - COLLECTOR_OTLP_ENABLED=true

Set the endpoint in your local environment:

.. code-block:: bash

    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

Access the Jaeger UI at ``http://localhost:16686`` to visualize traces.

AWS CloudWatch via OTEL Collector
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For CloudWatch, use the AWS Distro for OpenTelemetry (ADOT) Collector:

.. code-block:: yaml

    # docker-compose.production.yml or ECS task definition
    otel-collector:
      image: public.ecr.aws/aws-observability/aws-otel-collector:latest
      command: ["--config=/etc/otel-collector-config.yaml"]
      environment:
        - AWS_REGION=us-east-1
      volumes:
        - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml

Collector configuration:

.. code-block:: yaml

    # otel-collector-config.yaml
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318

    processors:
      batch:

    exporters:
      awsxray:
      awsemf:
        namespace: MyProject
        log_group_name: /myproject/traces

    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [awsxray]
        metrics:
          receivers: [otlp]
          processors: [batch]
          exporters: [awsemf]

Datadog via OTEL
^^^^^^^^^^^^^^^^

Datadog accepts OTLP directly. Set the endpoint to your Datadog agent:

.. code-block:: bash

    OTEL_EXPORTER_OTLP_ENDPOINT=http://datadog-agent:4317

Or use Datadog's native instrumentation for richer integration:

.. code-block:: text

    # requirements/production.txt
    ddtrace==2.17.0

.. code-block:: python

    # config/wsgi.py (alternative to OTEL)
    import os
    from ddtrace import patch_all, tracer

    # Configure before Django loads
    tracer.configure(
        hostname=os.environ.get("DD_AGENT_HOST", "localhost"),
        port=int(os.environ.get("DD_TRACE_AGENT_PORT", 8126)),
    )
    patch_all()

    from django.core.wsgi import get_wsgi_application
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
    application = get_wsgi_application()

Sending Logs to External Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For logs, you have two options:

**Option 1: Container log driver** (recommended for most setups)

Let your container orchestrator (ECS, Kubernetes) capture stdout and forward to CloudWatch/Datadog. Your JSON-formatted logs are already structured correctly.

**Option 2: Direct log shipping**

Use a log shipper like Fluent Bit or Vector alongside your application:

.. code-block:: yaml

    # docker-compose.production.yml
    fluent-bit:
      image: fluent/fluent-bit:latest
      volumes:
        - ./fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf
        - /var/log/app:/var/log/app:ro

Production Configuration Patterns
---------------------------------

Settings Organization
^^^^^^^^^^^^^^^^^^^^^

Keep observability configuration environment-aware:

.. code-block:: python

    # config/settings/base.py
    # Basic structlog setup (shared processors, formatters)
    # Console formatter defaults to pretty-print

    # config/settings/local.py
    # Inherits base, uses pretty console output
    # OTEL disabled by default (no OTEL_EXPORTER_OTLP_ENDPOINT)

    # config/settings/production.py
    LOGGING["handlers"]["console"]["formatter"] = "json"
    # OTEL configured via environment variables

Sampling Strategies
^^^^^^^^^^^^^^^^^^^

In high-traffic production, trace every request and you'll overwhelm your observability backend. Configure sampling:

.. code-block:: python

    # config/otel.py
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased

    def configure_opentelemetry():
        # Sample 10% of traces
        sampler = ParentBased(root=TraceIdRatioBased(0.1))

        provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )

For more sophisticated sampling (always trace errors, sample success):

.. code-block:: python

    from opentelemetry.sdk.trace.sampling import Sampler, Decision, SamplingResult

    class ErrorAwareSampler(Sampler):
        """Always sample errors, probabilistically sample success."""

        def __init__(self, rate=0.1):
            self.rate = rate

        def should_sample(self, parent_context, trace_id, name, kind, attributes, links):
            # Always sample if parent was sampled
            if parent_context and parent_context.trace_flags.sampled:
                return SamplingResult(Decision.RECORD_AND_SAMPLE)

            # Probabilistic sampling for root spans
            if (trace_id % 100) < (self.rate * 100):
                return SamplingResult(Decision.RECORD_AND_SAMPLE)

            return SamplingResult(Decision.DROP)

        def get_description(self):
            return f"ErrorAwareSampler({self.rate})"

Common Patterns
---------------

Correlation IDs Across Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When your Django app calls external services, propagate the trace context:

.. code-block:: python

    import httpx
    from opentelemetry.propagate import inject

    def call_external_service(url, data):
        headers = {}
        inject(headers)  # Adds traceparent header

        with httpx.Client() as client:
            response = client.post(url, json=data, headers=headers)
            return response.json()

Logging in Celery Tasks
^^^^^^^^^^^^^^^^^^^^^^^

Celery tasks run in separate processes. Ensure context is available:

.. code-block:: python

    # {project_slug}/orders/tasks.py
    import structlog
    from celery import shared_task
    from opentelemetry import trace

    logger = structlog.get_logger(__name__)
    tracer = trace.get_tracer(__name__)

    @shared_task(bind=True)
    def process_order(self, order_id):
        """Process an order asynchronously."""
        # Celery instrumentation automatically creates a span
        # Bind context for this task
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            task_id=self.request.id,
            order_id=order_id,
        )

        log = logger.bind()
        log.info("processing_order_started")

        try:
            order = Order.objects.get(id=order_id)
            # ... process order ...
            log.info("processing_order_completed")
        except Exception as e:
            log.exception("processing_order_failed")
            raise

Logging in Event Handlers
^^^^^^^^^^^^^^^^^^^^^^^^^

When using the :doc:`event-driven-architecture`, add context to event handlers:

.. code-block:: python

    # {project_slug}/orders/handlers.py
    import structlog
    from opentelemetry import trace

    logger = structlog.get_logger(__name__)
    tracer = trace.get_tracer(__name__)

    def handle_prescription_approved(event):
        """Handle prescription approval event."""
        with tracer.start_as_current_span("handle_prescription_approved") as span:
            span.set_attribute("event.type", type(event).__name__)
            span.set_attribute("prescription.id", event.prescription_id)

            log = logger.bind(
                event_type=type(event).__name__,
                prescription_id=event.prescription_id,
                order_uuid=event.order_uuid,
            )

            log.info("handling_prescription_approved")
            # ... handler logic ...

Complementing Sentry
^^^^^^^^^^^^^^^^^^^^

Sentry (if enabled in your project) captures errors automatically. Structured logging and OpenTelemetry complement Sentry by providing:

- **Pre-error context**: See what happened before the error
- **Performance data**: Identify slow operations before they become errors
- **Business metrics**: Track domain events beyond just errors

To correlate Sentry events with traces, add the trace ID:

.. code-block:: python

    # config/settings/production.py (if using Sentry)
    import sentry_sdk
    from opentelemetry import trace

    def before_send(event, hint):
        """Add trace context to Sentry events."""
        span = trace.get_current_span()
        if span.is_recording():
            ctx = span.get_span_context()
            event.setdefault("tags", {})["trace_id"] = format(ctx.trace_id, "032x")
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        before_send=before_send,
        # ... other config ...
    )

Summary
-------

Implementing observability requires these components:

**Packages**:

.. code-block:: text

    # requirements/base.txt
    structlog==24.4.0
    opentelemetry-api==1.29.0
    opentelemetry-sdk==1.29.0
    opentelemetry-instrumentation-django==0.50b0
    opentelemetry-instrumentation-psycopg2==0.50b0
    opentelemetry-instrumentation-redis==0.50b0
    opentelemetry-instrumentation-celery==0.50b0
    opentelemetry-exporter-otlp==1.29.0

**Key configuration points**:

1. **structlog configuration** in ``config/settings/base.py``—shared processors with environment-specific formatters
2. **Request context middleware** to automatically add request info to logs
3. **OpenTelemetry initialization** in ``config/wsgi.py`` or ``config/asgi.py``
4. **Environment variables** for OTLP endpoint and service name
5. **JSON formatter** in production settings

**Environment variables**:

.. code-block:: bash

    OTEL_SERVICE_NAME=myproject-api
    OTEL_EXPORTER_OTLP_ENDPOINT=http://collector:4317

**Development vs Production**:

+------------------+---------------------------+---------------------------+
| Aspect           | Development               | Production                |
+==================+===========================+===========================+
| Log format       | Pretty console            | JSON                      |
+------------------+---------------------------+---------------------------+
| Trace backend    | Jaeger (optional)         | CloudWatch/Datadog/etc    |
+------------------+---------------------------+---------------------------+
| Sampling         | 100%                      | 1-10% (configurable)      |
+------------------+---------------------------+---------------------------+
| OTEL enabled     | Optional                  | Required                  |
+------------------+---------------------------+---------------------------+

With these patterns in place, you'll have complete visibility into your application's behavior—from individual log statements to distributed traces across services—while maintaining a pleasant local development experience.
