"""
JSON-structured logging formatter for Cloud Logging compatibility.

Outputs structured JSON logs that Cloud Logging parses automatically,
enabling filtering by severity, model, token_count, etc.
"""

import json
import logging
import sys
from datetime import datetime, timezone


class CloudLoggingFormatter(logging.Formatter):
    """Formatter that outputs JSON compatible with Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_entry: dict = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        # Merge any extra fields (e.g., model, token_count, latency)
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in (
                    "name", "msg", "args", "created", "relativeCreated",
                    "exc_info", "exc_text", "stack_info", "lineno",
                    "funcName", "pathname", "filename", "module",
                    "levelno", "levelname", "message", "msecs",
                    "processName", "process", "threadName", "thread",
                    "taskName",
                ):
                    log_entry[key] = value

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    Create a logger with Cloud Logging-compatible JSON formatting.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(CloudLoggingFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
