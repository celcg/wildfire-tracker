"""Safe, environment-aware logging for the Wildfire Tracker API."""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

import config


LOGGER_NAMESPACE = "wildfire"
REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_control_characters = re.compile(r"[\x00-\x1f\x7f]+")


def _sanitize(value: object) -> object:
    """Remove secrets and control characters at the final output boundary."""
    if value is None or isinstance(value, (bool, int, float)):
        return value

    text = str(value)
    if config.NASA_KEY:
        text = text.replace(config.NASA_KEY, "[REDACTED]")
    return _control_characters.sub(" ", text)[:1000]


def _timestamp(record: logging.LogRecord) -> str:
    return datetime.fromtimestamp(record.created, timezone.utc).isoformat(
        timespec="milliseconds"
    ).replace("+00:00", "Z")


def _record_fields(record: logging.LogRecord) -> dict[str, object]:
    raw_fields = getattr(record, "event_fields", {})
    return {key: _sanitize(value) for key, value in raw_fields.items()}


class CloudJsonFormatter(logging.Formatter):
    """Emit one JSON object per line for Cloud Run structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        event = _sanitize(record.getMessage())
        payload = {
            "timestamp": _timestamp(record),
            "severity": record.levelname,
            "message": event,
            "event": event,
            **_record_fields(record),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class ReadableTextFormatter(logging.Formatter):
    """Keep local files compact, readable, and safe to parse line by line."""

    def format(self, record: logging.LogRecord) -> str:
        event = _sanitize(record.getMessage())
        fields = " ".join(
            f"{key}={json.dumps(value, ensure_ascii=False)}"
            for key, value in _record_fields(record).items()
        )
        prefix = f"{_timestamp(record)} | {record.levelname} | {event}"
        return f"{prefix} | {fields}" if fields else prefix


def configure_logging(
    *,
    log_to_file: bool | None = None,
    log_file_path: str | Path | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure handlers once and return the application logger."""
    logger = logging.getLogger(LOGGER_NAMESPACE)
    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    logger.propagate = False

    # App factories are created repeatedly in tests, so replace only handlers
    # owned by this module instead of accumulating duplicate log entries.
    for handler in list(logger.handlers):
        if getattr(handler, "_wildfire_handler", False):
            logger.removeHandler(handler)
            handler.close()

    console_handler = logging.StreamHandler(stream or sys.stdout)
    console_handler.setFormatter(CloudJsonFormatter())
    console_handler._wildfire_handler = True
    logger.addHandler(console_handler)

    should_log_to_file = config.LOG_TO_FILE if log_to_file is None else log_to_file
    if should_log_to_file:
        path = Path(log_file_path or config.LOG_FILE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path,
            maxBytes=max_bytes or config.LOG_MAX_BYTES,
            backupCount=(
                config.LOG_BACKUP_COUNT
                if backup_count is None
                else backup_count
            ),
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(ReadableTextFormatter())
        file_handler._wildfire_handler = True
        logger.addHandler(file_handler)

    # The middleware below is the canonical application access log. Keeping a
    # second Uvicorn line would double ingestion without adding correlation.
    logging.getLogger("uvicorn.access").disabled = True
    return logger


def get_logger(component: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAMESPACE}.{component}")


def bind_request_id(request_id: str) -> Token:
    return _request_id.set(request_id)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def current_request_id() -> str:
    return _request_id.get()


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: object,
) -> None:
    """Write a named event without accepting free-form log templates."""
    request_id = current_request_id()
    if request_id != "-":
        fields = {"request_id": request_id, **fields}
    logger.log(level, event, extra={"event_fields": fields})
