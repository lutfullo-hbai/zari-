"""
Structured logging configuration for Zari
Provides JSON-formatted logs with structured fields
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any

from core.config import settings


class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-structured logs"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add additional fields
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "intent"):
            log_data["intent"] = record.intent
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Include extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger(logging.Logger):
    """Custom logger that supports structured fields"""

    def log_event(self, level: int, message: str, **extra_fields) -> None:
        """Log with extra structured fields"""
        record = self.makeRecord(
            self.name,
            level,
            None,
            None,
            message,
            (),
            None,
        )
        record.extra_fields = extra_fields
        self.handle(record)

    def info_event(self, message: str, **extra_fields) -> None:
        """Log info with extra fields"""
        self.log_event(logging.INFO, message, **extra_fields)

    def error_event(self, message: str, **extra_fields) -> None:
        """Log error with extra fields"""
        self.log_event(logging.ERROR, message, **extra_fields)

    def warning_event(self, message: str, **extra_fields) -> None:
        """Log warning with extra fields"""
        self.log_event(logging.WARNING, message, **extra_fields)

    def debug_event(self, message: str, **extra_fields) -> None:
        """Log debug with extra fields"""
        self.log_event(logging.DEBUG, message, **extra_fields)


def configure_logging() -> logging.Logger:
    """
    Configure structured logging for Zari

    Returns:
        Configured logger instance
    """
    # Set custom logger class
    logging.setLoggerClass(StructuredLogger)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Set formatter based on configuration
    if settings.log_format.lower() == "json":
        formatter = JsonFormatter()
    else:
        # Default text formatter
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Get logger for zari
    zari_logger = logging.getLogger("zari")
    zari_logger.info("Logging configured - level: %s, format: %s", settings.log_level.upper(), settings.log_format)

    return zari_logger


# Configure logging when module is imported
_default_logger = configure_logging()


def get_logger(name: str) -> StructuredLogger:
    """
    Get a named logger

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured StructuredLogger instance
    """
    logger = logging.getLogger(name)
    if not isinstance(logger, StructuredLogger):
        logging.setLoggerClass(StructuredLogger)
        logger = logging.getLogger(name)
    return logger


if __name__ == "__main__":
    # Test logging configuration
    logger = get_logger("zari.test")

    logger.info("Simple info message")
    logger.warning("Warning message")
    logger.error("Error message")

    logger.info_event("Event with extra fields", user_id="user123", session_id="sess456")

    try:
        1 / 0
    except Exception:
        logger.exception("An error occurred")

    logger.debug_event("Debug event", component="router", duration_ms=42)
