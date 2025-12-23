"""Structured logging configuration using structlog.

This module configures structlog for the LEADR application with support for:
- JSON output for production (machine-parseable)
- Colored console output for development (human-readable)
- File logging with rotation
- Integration with standard library logging (captures third-party logs)
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog

# ANSI color codes for console output
_COLORS = {
    "debug": "\033[36m",  # Cyan
    "info": "\033[32m",  # Green
    "warning": "\033[33m",  # Yellow
    "error": "\033[31m",  # Red
    "critical": "\033[35m",  # Magenta
}
_RESET = "\033[0m"
_DIM = "\033[2m"


def _console_renderer(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> str:
    """Custom console renderer matching the original LEADR log format.

    Format: timestamp|app|env|server [LEVEL] logger:func:line - message key=value
    """
    # Extract standard fields
    timestamp = event_dict.pop("timestamp", "")
    level = event_dict.pop("level", "info").upper()
    logger_name = event_dict.pop("logger", "")
    func_name = event_dict.pop("func_name", "")
    lineno = event_dict.pop("lineno", "")
    app = event_dict.pop("app", "LEADR")
    env = event_dict.pop("env", "")
    event = event_dict.pop("event", "")
    exception = event_dict.pop("exception", None)

    # Build location string
    location = logger_name
    if func_name:
        location = f"{location}:{func_name}"
    if lineno:
        location = f"{location}:{lineno}"

    # Format extra key=value pairs
    extras = ""
    if event_dict:
        extras = " " + " ".join(f"{k}={v}" for k, v in event_dict.items())

    # Apply colors
    color = _COLORS.get(level.lower(), "")
    level_str = f"{color}[{level}]{_RESET}"
    dim_location = f"{_DIM}{location}{_RESET}"

    log_line = f"{timestamp}|{app}|{env}|server {level_str} {dim_location} - {event}{extras}"

    if exception:
        return f"{log_line}\n{exception}"
    return log_line


def _add_app_context(app_name: str, env: str) -> structlog.types.Processor:
    """Create a processor that adds app and env context to log entries."""

    def processor(
        logger: logging.Logger,
        method_name: str,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        event_dict["app"] = app_name
        event_dict["env"] = env
        return event_dict

    return processor


def setup_logging(
    *,
    log_level: str = "INFO",
    json_format: bool = True,
    log_to_file: bool = False,
    log_dir: Path = Path("/var/log/leadr"),
    app_name: str = "LEADR",
    env: str = "PROD",
) -> None:
    """Configure structlog for the application.

    This function sets up structured logging using structlog with integration
    to the standard library logging module. This allows both structlog loggers
    and standard library loggers (used by third-party packages like uvicorn)
    to be processed through the same pipeline.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format (True) or colored console (False)
        log_to_file: Enable file logging in addition to stdout
        log_dir: Directory for log files when log_to_file is enabled
        app_name: Application name added to each log entry
        env: Environment name added to each log entry
    """
    # Shared processors for all log entries
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_app_context(app_name, env),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if json_format:
        # Production: JSON output
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Development: colored console output matching original LEADR format
        renderer = _console_renderer

    # Configure structlog
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    handlers: list[logging.Handler] = [console_handler]

    # File handler (optional)
    if log_to_file:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10_485_760,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = handlers
    root_logger.setLevel(log_level)

    # Configure uvicorn loggers to use our handlers
    # Note: uvicorn.access is disabled - we use AccessLogMiddleware for access logging with timing
    for logger_name in ["uvicorn", "uvicorn.error"]:
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers = handlers
        uv_logger.propagate = False

    # Disable uvicorn's access logger (replaced by AccessLogMiddleware)
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        A bound structlog logger that can be used for structured logging

    Example:
        >>> from leadr.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("User created", user_id="abc-123")
    """
    return structlog.get_logger(name)


def bind_contextvars(**kwargs: Any) -> None:
    """Bind context variables that will be included in all subsequent log entries.

    This is useful for adding request-scoped context like request_id that should
    appear in all logs within that context.

    Args:
        **kwargs: Key-value pairs to bind to the context

    Example:
        >>> from leadr.logging import bind_contextvars
        >>> bind_contextvars(request_id="req-123", user_id="user-456")
        >>> # All subsequent logs will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_contextvars() -> None:
    """Clear all bound context variables.

    Call this at the start of a new request to ensure no context leaks
    between requests.
    """
    structlog.contextvars.clear_contextvars()
