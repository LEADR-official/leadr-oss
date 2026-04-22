"""Tests for API exception handlers."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from leadr.common.api.exceptions import (
    catchall_exception_handler,
    entity_not_found_handler,
    http_exception_handler,
    validation_error_handler,
)
from leadr.common.domain.exceptions import EntityNotFoundError


class TestCatchallExceptionHandler:
    """Tests for catchall_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_500_status(self) -> None:
        """Handler should return 500 status code."""
        mock_request = MagicMock(spec=Request)
        exc = Exception("Something went wrong")

        response = await catchall_exception_handler(mock_request, exc)

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_includes_error_message_when_debug_enabled(self) -> None:
        """Handler should include exception message when DEBUG is True."""
        mock_request = MagicMock(spec=Request)
        exc = Exception("Detailed error message")

        with patch("leadr.common.api.exceptions.settings") as mock_settings:
            mock_settings.DEBUG = True
            response = await catchall_exception_handler(mock_request, exc)

        assert response.body == b'{"error":"Detailed error message"}'

    @pytest.mark.asyncio
    async def test_hides_error_message_when_debug_disabled(self) -> None:
        """Handler should hide exception message when DEBUG is False."""
        mock_request = MagicMock(spec=Request)
        exc = Exception("Secret error details")

        with patch("leadr.common.api.exceptions.settings") as mock_settings:
            mock_settings.DEBUG = False
            response = await catchall_exception_handler(mock_request, exc)

        assert response.body == b'{"error":"Internal server error"}'

    @pytest.mark.asyncio
    async def test_logs_account_id_when_available(self) -> None:
        """Handler should include account_id in log extra when set on request.state."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.account_id = "test-account-123"
        mock_request.state.game_id = None
        exc = Exception("Test error")

        with patch("leadr.common.api.exceptions.logger") as mock_logger:
            await catchall_exception_handler(mock_request, exc)

            mock_logger.exception.assert_called_once()
            call_kwargs = mock_logger.exception.call_args[1]
            assert call_kwargs["extra"]["account_id"] == "test-account-123"

    @pytest.mark.asyncio
    async def test_logs_game_id_when_available(self) -> None:
        """Handler should include game_id in log extra when set on request.state."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.account_id = "test-account-123"
        mock_request.state.game_id = "test-game-456"
        exc = Exception("Test error")

        with patch("leadr.common.api.exceptions.logger") as mock_logger:
            await catchall_exception_handler(mock_request, exc)

            mock_logger.exception.assert_called_once()
            call_kwargs = mock_logger.exception.call_args[1]
            assert call_kwargs["extra"]["game_id"] == "test-game-456"

    @pytest.mark.asyncio
    async def test_handles_missing_state_attributes(self) -> None:
        """Handler should gracefully handle missing account_id/game_id on request.state."""
        mock_request = MagicMock(spec=Request)
        # Simulate state without account_id or game_id attributes
        del mock_request.state.account_id
        del mock_request.state.game_id
        exc = Exception("Test error")

        with patch("leadr.common.api.exceptions.logger") as mock_logger:
            response = await catchall_exception_handler(mock_request, exc)

            assert response.status_code == 500
            call_kwargs = mock_logger.exception.call_args[1]
            assert call_kwargs["extra"]["account_id"] is None
            assert call_kwargs["extra"]["game_id"] is None


class TestHttpExceptionHandler:
    """Tests for http_exception_handler."""

    @pytest.mark.asyncio
    async def test_returns_correct_status_code(self) -> None:
        """Handler should return the HTTP exception's status code."""
        mock_request = MagicMock(spec=Request)
        exc = HTTPException(status_code=403, detail="Forbidden")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_includes_error_detail(self) -> None:
        """Handler should include the exception detail in the response."""
        mock_request = MagicMock(spec=Request)
        exc = HTTPException(status_code=400, detail="Bad request data")

        response = await http_exception_handler(mock_request, exc)

        assert response.body == b'{"error":"Bad request data"}'

    @pytest.mark.asyncio
    async def test_handles_401_unauthorized(self) -> None:
        """Handler should correctly handle 401 Unauthorized."""
        mock_request = MagicMock(spec=Request)
        exc = HTTPException(status_code=401, detail="Authentication required")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 401
        assert response.body == b'{"error":"Authentication required"}'

    @pytest.mark.asyncio
    async def test_logs_context_for_500_errors(self) -> None:
        """Handler should include account_id and game_id in log for 500+ errors."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.account_id = "test-account-123"
        mock_request.state.game_id = "test-game-456"
        exc = HTTPException(status_code=500, detail="Internal error")

        with patch("leadr.common.api.exceptions.logger") as mock_logger:
            await http_exception_handler(mock_request, exc)

            mock_logger.exception.assert_called_once()
            call_kwargs = mock_logger.exception.call_args[1]
            assert call_kwargs["extra"]["account_id"] == "test-account-123"
            assert call_kwargs["extra"]["game_id"] == "test-game-456"

    @pytest.mark.asyncio
    async def test_handles_missing_state_for_500_errors(self) -> None:
        """Handler should gracefully handle missing state attributes for 500+ errors."""
        mock_request = MagicMock(spec=Request)
        del mock_request.state.account_id
        del mock_request.state.game_id
        exc = HTTPException(status_code=502, detail="Bad gateway")

        with patch("leadr.common.api.exceptions.logger") as mock_logger:
            response = await http_exception_handler(mock_request, exc)

            assert response.status_code == 502
            call_kwargs = mock_logger.exception.call_args[1]
            assert call_kwargs["extra"]["account_id"] is None
            assert call_kwargs["extra"]["game_id"] is None


class TestEntityNotFoundHandler:
    """Tests for entity_not_found_handler."""

    @pytest.mark.asyncio
    async def test_returns_404_status(self) -> None:
        """Handler should return 404 status code."""
        mock_request = MagicMock(spec=Request)
        exc = EntityNotFoundError("Account", "123e4567-e89b-12d3-a456-426614174000")

        response = await entity_not_found_handler(mock_request, exc)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_includes_entity_type_in_message(self) -> None:
        """Handler should include entity type in error message."""
        mock_request = MagicMock(spec=Request)
        exc = EntityNotFoundError("Game", "abc-123")

        response = await entity_not_found_handler(mock_request, exc)

        assert response.body == b'{"error":"Game not found"}'

    @pytest.mark.asyncio
    async def test_handles_various_entity_types(self) -> None:
        """Handler should work with different entity types."""
        mock_request = MagicMock(spec=Request)

        for entity_type in ["User", "Board", "Score", "Device"]:
            exc = EntityNotFoundError(entity_type, "test-id")
            response = await entity_not_found_handler(mock_request, exc)
            expected = f'{{"error":"{entity_type} not found"}}'.encode()
            assert response.body == expected


class TestValidationErrorHandler:
    """Tests for validation_error_handler."""

    @pytest.mark.asyncio
    async def test_returns_422_status(self) -> None:
        """Handler should return 422 status code."""
        mock_request = MagicMock(spec=Request)
        exc = RequestValidationError(errors=[])

        response = await validation_error_handler(mock_request, exc)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_includes_validation_errors(self) -> None:
        """Handler should include validation errors in response."""
        mock_request = MagicMock(spec=Request)
        validation_errors = [
            {
                "type": "missing",
                "loc": ("body", "name"),
                "msg": "Field required",
                "input": {},
            }
        ]
        exc = RequestValidationError(errors=validation_errors)

        response = await validation_error_handler(mock_request, exc)

        body = json.loads(bytes(response.body))
        assert "error" in body
        assert len(body["error"]) == 1
        assert body["error"][0]["loc"] == ["body", "name"]
        assert body["error"][0]["msg"] == "Field required"

    @pytest.mark.asyncio
    async def test_includes_request_body(self) -> None:
        """Handler should include the request body in response."""
        mock_request = MagicMock(spec=Request)
        request_body = {"invalid_field": "value"}
        exc = RequestValidationError(errors=[], body=request_body)

        response = await validation_error_handler(mock_request, exc)

        body = json.loads(bytes(response.body))
        assert "body" in body
        assert body["body"] == {"invalid_field": "value"}

    @pytest.mark.asyncio
    async def test_handles_multiple_validation_errors(self) -> None:
        """Handler should include all validation errors."""
        mock_request = MagicMock(spec=Request)
        validation_errors = [
            {
                "type": "missing",
                "loc": ("body", "name"),
                "msg": "Field required",
                "input": {},
            },
            {
                "type": "string_type",
                "loc": ("body", "email"),
                "msg": "Input should be a valid string",
                "input": 123,
            },
        ]
        exc = RequestValidationError(errors=validation_errors)

        response = await validation_error_handler(mock_request, exc)

        body = json.loads(bytes(response.body))
        assert len(body["error"]) == 2
