"""Email domain interfaces."""

from abc import ABC, abstractmethod
from typing import Any

from leadr.infra.email.domain.models import Email


class EmailProvider(ABC):
    """Interface for email service providers."""

    @abstractmethod
    def send(self, email: Email) -> dict[str, Any]:
        """Send an email and return provider response."""

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration."""
