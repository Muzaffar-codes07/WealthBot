"""
WealthBot Structured Logging
============================
Structlog configuration for JSON (production) and console (development) output.
"""

import logging
import sys

import structlog

from app.core.config import settings
from app.core.security import sanitize_log_data


def _pii_mask_processor(
    _logger: object, _method: str, event_dict: dict[str, object]
) -> dict[str, object]:
    """Structlog processor that redacts secrets and masks PII in every log event."""
    return sanitize_log_data(event_dict)  # type: ignore[return-value]


def configure_logging() -> None:
    """Set up structlog with environment-aware renderers.

    - Production / staging → JSON lines (machine-parseable).
    - Development / testing → coloured console output.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _pii_mask_processor,
    ]

    if settings.app_env in ("production", "staging"):
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level)
