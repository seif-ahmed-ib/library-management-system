from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from app.core.config import settings


STANDARD_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def to_dict(self, record: logging.LogRecord) -> dict[str, Any]:
        event = record.getMessage()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": event,
        }

        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_RECORD_FIELDS:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return payload

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            self.to_dict(record),
            default=str,
            ensure_ascii=False,
        )


class RecentLogHandler(logging.Handler):
    def __init__(self, capacity: int = 200) -> None:
        super().__init__()
        self.records: deque[dict[str, Any]] = deque(maxlen=capacity)
        self.json_formatter = JsonFormatter()

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.json_formatter.to_dict(record))

    def clear(self) -> None:
        self.records.clear()


recent_log_handler = RecentLogHandler()


def configure_logging() -> None:
    library_logger = logging.getLogger("library")

    if getattr(library_logger, "_library_configured", False):
        return

    level = getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    )
    formatter = JsonFormatter()
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    recent_log_handler.setLevel(logging.DEBUG)

    library_logger.setLevel(level)
    library_logger.addHandler(stream_handler)
    library_logger.addHandler(file_handler)
    library_logger.addHandler(recent_log_handler)
    library_logger.propagate = False
    library_logger._library_configured = True  # type: ignore[attr-defined]


def get_recent_logs(
    minimum_level: int = logging.WARNING,
    limit: int = 20,
) -> list[dict[str, Any]]:
    level_values = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    matching_records = [
        record
        for record in recent_log_handler.records
        if level_values.get(record["level"], 0) >= minimum_level
    ]
    return matching_records[-limit:][::-1]


def clear_recent_logs() -> None:
    recent_log_handler.clear()
