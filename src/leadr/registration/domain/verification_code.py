"""Verification code domain models for email verification during registration."""

import re
from datetime import UTC, datetime
from enum import Enum

from pydantic import EmailStr, Field, field_validator

from leadr.common.domain.ids import UserID
from leadr.common.domain.models import Entity


class VerificationCodeStatus(Enum):
    """Verification code status enumeration."""

    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"


class VerificationCodeType(str, Enum):
    """Verification code type enumeration.

    Distinguishes between codes used for initial registration
    and codes used for user invitations.
    """

    REGISTRATION = "registration"
    """Code for new account registration flow."""

    INVITE = "invite"
    """Code for invited user to join an existing account."""


class VerificationCode(Entity):
    """Verification code domain entity.

    Represents a one-time email verification code used during registration or invite flows.
    Codes are 6-character alphanumeric strings with configurable expiration windows
    (10 minutes for registration, 24 hours for invites by default).
    Once used or expired, codes become invalid and cannot be reused.

    The code_type field distinguishes between REGISTRATION codes (for new account signup)
    and INVITE codes (for invited users joining an existing account).
    """

    email: EmailStr = Field(description="Email address this code was sent to")
    code: str = Field(
        description="6-character alphanumeric verification code (case-insensitive)",
        min_length=6,
        max_length=6,
    )
    status: VerificationCodeStatus = VerificationCodeStatus.PENDING
    code_type: VerificationCodeType = Field(
        default=VerificationCodeType.REGISTRATION,
        description="Type of verification code (registration or invite)",
    )
    user_id: UserID | None = Field(
        default=None,
        description="User ID for invite codes (links invite to existing user record)",
    )
    expires_at: datetime = Field(description="When this code expires (UTC)")
    used_at: datetime | None = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Validate and normalize the verification code.

        Args:
            v: The code value to validate.

        Returns:
            The normalized (uppercase) code.

        Raises:
            ValueError: If the code contains non-alphanumeric characters.
        """
        if not re.match(r"^[a-zA-Z0-9]{6}$", v):
            raise ValueError("code must be exactly 6 alphanumeric characters")
        return v.upper()  # Normalize to uppercase

    def is_expired(self) -> bool:
        """Check if the verification code has expired.

        Returns:
            True if the code's expiration time has passed.
        """
        return datetime.now(UTC) > self.expires_at

    def is_used(self) -> bool:
        """Check if the verification code has been used.

        Returns:
            True if the code status is USED.
        """
        return self.status == VerificationCodeStatus.USED

    def is_valid(self) -> bool:
        """Check if the verification code is valid and can be used.

        A code is valid if it hasn't been used and hasn't expired.

        Returns:
            True if the code is valid and can be used for verification.
        """
        return not self.is_used() and not self.is_expired()

    def mark_as_used(self) -> None:
        """Mark the verification code as used.

        Sets the status to USED and records the current timestamp in used_at.
        Once marked as used, the code cannot be reused.
        """
        self.status = VerificationCodeStatus.USED
        self.used_at = datetime.now(UTC)

    def mark_as_expired(self) -> None:
        """Mark the verification code as expired.

        Sets the status to EXPIRED. This is typically done when cleaning up
        old codes or when explicitly invalidating codes.
        """
        self.status = VerificationCodeStatus.EXPIRED

    @property
    def is_invite(self) -> bool:
        """Check if this is an invite code."""
        return self.code_type == VerificationCodeType.INVITE

    @property
    def is_registration(self) -> bool:
        """Check if this is a registration code."""
        return self.code_type == VerificationCodeType.REGISTRATION
