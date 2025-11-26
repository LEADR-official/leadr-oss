"""Tests for email domain exceptions."""

import pytest

from leadr.infra.email.domain.exceptions import (
    EmailError,
    EmailSendError,
    EmailValidationError,
)


class TestEmailError:
    """Test EmailError base exception."""

    def test_can_be_raised(self):
        """Test that EmailError can be raised."""
        with pytest.raises(EmailError, match="Test error"):
            raise EmailError("Test error")

    def test_inherits_from_exception(self):
        """Test that EmailError inherits from Exception."""
        assert issubclass(EmailError, Exception)


class TestEmailValidationError:
    """Test EmailValidationError."""

    def test_can_be_raised(self):
        """Test that EmailValidationError can be raised."""
        with pytest.raises(EmailValidationError, match="Invalid email"):
            raise EmailValidationError("Invalid email")

    def test_inherits_from_email_error(self):
        """Test that EmailValidationError inherits from EmailError."""
        assert issubclass(EmailValidationError, EmailError)

    def test_can_be_caught_as_email_error(self):
        """Test that EmailValidationError can be caught as EmailError."""
        with pytest.raises(EmailError):
            raise EmailValidationError("Invalid email")


class TestEmailSendError:
    """Test EmailSendError."""

    def test_can_be_raised(self):
        """Test that EmailSendError can be raised."""
        with pytest.raises(EmailSendError, match="Send failed"):
            raise EmailSendError("Send failed")

    def test_inherits_from_email_error(self):
        """Test that EmailSendError inherits from EmailError."""
        assert issubclass(EmailSendError, EmailError)

    def test_can_be_caught_as_email_error(self):
        """Test that EmailSendError can be caught as EmailError."""
        with pytest.raises(EmailError):
            raise EmailSendError("Send failed")

    def test_with_provider_response(self):
        """Test EmailSendError with provider response."""
        provider_response = {"error": "Invalid API key", "status": 401}
        error = EmailSendError("Authentication failed", provider_response)

        assert str(error) == "Authentication failed"
        assert error.provider_response == provider_response

    def test_without_provider_response(self):
        """Test EmailSendError without provider response."""
        error = EmailSendError("Network timeout")

        assert str(error) == "Network timeout"
        assert error.provider_response is None

    def test_provider_response_defaults_to_none(self):
        """Test that provider_response defaults to None."""
        error = EmailSendError("Test error")
        assert error.provider_response is None
