"""Structured logging with PII redaction.

Sets up *structlog* with JSON rendering and a custom processor that strips
personally-identifiable information (names, phone numbers, email addresses)
before any log line is emitted.  Nothing in this module imports domain or
storage layers — it is safe to initialise early.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog

# ── PII patterns ────────────────────────────────────────────────────────
_PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,15}\d")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

# Keys whose values must always be redacted regardless of pattern match.
_REDACT_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "client_name",
        "first_name",
        "last_name",
        "phone",
        "phone_number",
        "mobile",
        "email",
        "email_address",
        "address",
        "message_content",
        "message_body",
        "draft_text",
    }
)


def _redact_value(value: object) -> object:
    """Replace PII patterns in a string value."""
    if not isinstance(value, str):
        return value
    value = _PHONE_RE.sub("[REDACTED_PHONE]", value)
    return _EMAIL_RE.sub("[REDACTED_EMAIL]", value)


def pii_redactor(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Structlog processor that scrubs PII from all event dict values."""
    redacted: dict[str, Any] = {}
    for key, value in event_dict.items():
        if key in _REDACT_KEYS:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = _redact_value(value)
    return redacted


def setup_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    """Configure structlog and stdlib logging.

    Parameters
    ----------
    level:
        Log level name (``DEBUG``, ``INFO``, etc.).
    json_output:
        If ``True``, render logs as JSON.  ``False`` uses coloured console
        output (useful during development).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Stdlib root logger — capture third-party logs too.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
        force=True,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        pii_redactor,
    ]

    if json_output:
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

    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(formatter)
    root.setLevel(log_level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
