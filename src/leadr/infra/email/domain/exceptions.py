"""Email domain exceptions."""

from typing import Any


class EmailError(Exception):
    """Base exception for email domain errors."""


class EmailValidationError(EmailError):
    """Raised when email validation fails."""


class EmailSendError(EmailError):
    """Raised when email sending fails."""

    def __init__(self, message: str, provider_response: dict[str, Any] | None = None):
        super().__init__(message)
        self.provider_response = provider_response
