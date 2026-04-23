"""
Production-grade logging configuration.
Provides structured JSON logging for production and readable logs for development.
"""
import logging
import logging.handlers
import sys
import json
from datetime import datetime, timezone
from typing import Optional
import os


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "business_id"):
            log_data["business_id"] = record.business_id

        return json.dumps(log_data)


class ColorFormatter(logging.Formatter):
    """Colored log formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[1;31m", # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(debug: bool = False, log_dir: str = "./logs") -> logging.Logger:
    """
    Configure application logging.

    Args:
        debug: Enable debug mode (colored console output)
        log_dir: Directory for log files

    Returns:
        Root application logger
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("devtrack")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if debug:
        console_handler.setFormatter(ColorFormatter(
            "%(asctime)s %(levelname)s [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
            datefmt="%H:%M:%S"
        ))
    else:
        console_handler.setFormatter(JSONFormatter())
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(console_handler)

    # File handler — rotating daily, keep 30 days
    file_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # Error file handler — separate error-only log
    error_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    logger.addHandler(error_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return logger


# Initialize logger
logger = setup_logging(debug=os.getenv("DEBUG", "true").lower() == "true")
