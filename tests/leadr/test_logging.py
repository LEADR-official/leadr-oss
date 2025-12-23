"""Tests for the structured logging module."""

import json
import logging
import tempfile
from io import StringIO
from pathlib import Path

import pytest
import structlog

from leadr.logging import (
    bind_contextvars,
    clear_contextvars,
    get_logger,
    setup_logging,
)


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Clear structlog contextvars
    clear_contextvars()

    # Reset structlog configuration
    structlog.reset_defaults()

    yield

    # Clean up after test
    clear_contextvars()
    structlog.reset_defaults()


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_configures_root_logger(self):
        """setup_logging should configure the root logger."""
        setup_logging(log_level="INFO", json_format=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) >= 1

    def test_setup_logging_debug_level(self):
        """setup_logging should set DEBUG level when specified."""
        setup_logging(log_level="DEBUG", json_format=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_json_format_produces_json(self):
        """JSON format should produce valid JSON output."""
        setup_logging(log_level="INFO", json_format=True)

        # Capture stdout
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.getLogger().handlers[0].formatter)

        test_logger = logging.getLogger("test.json")
        test_logger.handlers = [handler]
        test_logger.setLevel(logging.INFO)

        test_logger.info("Test message")

        output = stream.getvalue()
        assert output.strip()  # Should have output

        # Should be valid JSON
        log_entry = json.loads(output.strip())
        assert "event" in log_entry
        assert log_entry["event"] == "Test message"
        assert "level" in log_entry
        assert log_entry["level"] == "info"

    def test_setup_logging_console_format_produces_readable_output(self):
        """Console format should produce human-readable output."""
        setup_logging(log_level="INFO", json_format=False)

        # Capture stdout
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.getLogger().handlers[0].formatter)

        test_logger = logging.getLogger("test.console")
        test_logger.handlers = [handler]
        test_logger.setLevel(logging.INFO)

        test_logger.info("Test message")

        output = stream.getvalue()
        assert output.strip()  # Should have output

        # Should NOT be valid JSON (it's colored console output)
        try:
            json.loads(output.strip())
            # If we get here, it parsed as JSON, which means it's not console format
            pytest.fail("Console format should not produce JSON")
        except json.JSONDecodeError:
            pass  # Expected - console format is not JSON

    def test_setup_logging_with_file_creates_file_handler(self):
        """LOG_TO_FILE should create a file handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            setup_logging(
                log_level="INFO",
                json_format=True,
                log_to_file=True,
                log_dir=log_dir,
            )

            # Log a message
            test_logger = logging.getLogger("test.file")
            test_logger.info("Test file message")

            # Check that log file was created
            log_file = log_dir / "app.log"
            assert log_file.exists()

            # Check content
            content = log_file.read_text()
            assert "Test file message" in content

    def test_setup_logging_creates_log_directory(self):
        """setup_logging should create log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "nested" / "log" / "dir"
            assert not log_dir.exists()

            setup_logging(
                log_level="INFO",
                json_format=True,
                log_to_file=True,
                log_dir=log_dir,
            )

            assert log_dir.exists()

    def test_setup_logging_adds_app_and_env_to_logs(self):
        """App name and environment should be added to log entries."""
        setup_logging(
            log_level="INFO",
            json_format=True,
            app_name="TestApp",
            env="TestEnv",
        )

        # Capture stdout
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.getLogger().handlers[0].formatter)

        test_logger = logging.getLogger("test.app_env")
        test_logger.handlers = [handler]
        test_logger.setLevel(logging.INFO)

        test_logger.info("Test message")

        output = stream.getvalue()
        log_entry = json.loads(output.strip())
        assert log_entry["app"] == "TestApp"
        assert log_entry["env"] == "TestEnv"

    def test_setup_logging_configures_uvicorn_loggers(self):
        """Uvicorn loggers should be configured with our handlers.

        Note: uvicorn.access is disabled because we use AccessLogMiddleware instead.
        """
        setup_logging(log_level="INFO", json_format=True)

        # uvicorn and uvicorn.error should have handlers
        for logger_name in ["uvicorn", "uvicorn.error"]:
            uv_logger = logging.getLogger(logger_name)
            assert len(uv_logger.handlers) >= 1
            assert uv_logger.propagate is False

        # uvicorn.access should be disabled (replaced by AccessLogMiddleware)
        access_logger = logging.getLogger("uvicorn.access")
        assert access_logger.disabled is True


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_bound_logger(self):
        """get_logger should return a structlog BoundLogger."""
        setup_logging(log_level="INFO", json_format=True)

        logger = get_logger("test.module")

        assert logger is not None
        # Should have standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_get_logger_can_log_with_extra_fields(self):
        """Structlog logger should support logging with extra fields."""
        setup_logging(log_level="INFO", json_format=True)

        # Capture stdout
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.getLogger().handlers[0].formatter)

        root = logging.getLogger()
        original_handlers = root.handlers
        root.handlers = [handler]

        try:
            logger = get_logger("test.extra")
            logger.info("User action", user_id="123", action="login")

            output = stream.getvalue()
            log_entry = json.loads(output.strip())
            assert log_entry["user_id"] == "123"
            assert log_entry["action"] == "login"
        finally:
            root.handlers = original_handlers


class TestContextvars:
    """Tests for context variable binding."""

    def test_bind_contextvars_adds_to_logs(self):
        """bind_contextvars should add values to all subsequent logs."""
        setup_logging(log_level="INFO", json_format=True)

        # Capture stdout
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.getLogger().handlers[0].formatter)

        root = logging.getLogger()
        original_handlers = root.handlers
        root.handlers = [handler]

        try:
            bind_contextvars(request_id="req-456")

            logger = get_logger("test.context")
            logger.info("Request processed")

            output = stream.getvalue()
            log_entry = json.loads(output.strip())
            assert log_entry["request_id"] == "req-456"
        finally:
            root.handlers = original_handlers

    def test_clear_contextvars_removes_bound_values(self):
        """clear_contextvars should remove all bound context values."""
        setup_logging(log_level="INFO", json_format=True)

        bind_contextvars(request_id="req-789")
        clear_contextvars()

        # Capture stdout
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.getLogger().handlers[0].formatter)

        root = logging.getLogger()
        original_handlers = root.handlers
        root.handlers = [handler]

        try:
            logger = get_logger("test.clear")
            logger.info("After clear")

            output = stream.getvalue()
            log_entry = json.loads(output.strip())
            assert "request_id" not in log_entry
        finally:
            root.handlers = original_handlers
