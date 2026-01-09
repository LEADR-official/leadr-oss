"""Tests for VerificationCode domain model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.common.domain.ids import UserID
from leadr.registration.domain.verification_code import (
    VerificationCode,
    VerificationCodeStatus,
    VerificationCodeType,
)


class TestVerificationCodeStatus:
    """Test suite for VerificationCodeStatus enum."""

    def test_status_enum_values(self):
        """Test that VerificationCodeStatus has correct enum values."""
        assert VerificationCodeStatus.PENDING.value == "pending"
        assert VerificationCodeStatus.USED.value == "used"
        assert VerificationCodeStatus.EXPIRED.value == "expired"


class TestVerificationCode:
    """Test suite for VerificationCode domain model."""

    def test_create_verification_code_with_valid_data(self):
        """Test creating a verification code with all required fields."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.PENDING,
            expires_at=expires_at,
            created_at=now,
            used_at=None,
        )

        assert code.email == "user@example.com"
        assert code.code == "ABC123"
        assert code.status == VerificationCodeStatus.PENDING
        assert code.expires_at == expires_at
        assert code.created_at == now
        assert code.used_at is None

    def test_create_verification_code_defaults_to_pending_status(self):
        """Test that verification code status defaults to PENDING."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            expires_at=expires_at,
            created_at=now,
        )

        assert code.status == VerificationCodeStatus.PENDING

    def test_email_required(self):
        """Test that email is required."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        with pytest.raises(ValidationError) as exc_info:
            VerificationCode(  # type: ignore[call-arg]
                code="ABC123",
                expires_at=expires_at,
                created_at=now,
            )

        assert "email" in str(exc_info.value)

    def test_code_required(self):
        """Test that code is required."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        with pytest.raises(ValidationError) as exc_info:
            VerificationCode(  # type: ignore[call-arg]
                email="user@example.com",
                expires_at=expires_at,
                created_at=now,
            )

        assert "code" in str(exc_info.value)

    def test_expires_at_required(self):
        """Test that expires_at is required."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            VerificationCode(  # type: ignore[call-arg]
                email="user@example.com",
                code="ABC123",
                created_at=now,
            )

        assert "expires_at" in str(exc_info.value)

    def test_code_accepts_valid_6_char_alphanumeric(self):
        """Test that code accepts valid 6-character alphanumeric strings."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        valid_codes = ["ABC123", "XYZ789", "A1B2C3", "123456", "ABCDEF"]

        for valid_code in valid_codes:
            code = VerificationCode(
                email="user@example.com",
                code=valid_code,
                expires_at=expires_at,
                created_at=now,
            )
            assert code.code == valid_code

    def test_code_rejects_too_short(self):
        """Test that code rejects strings shorter than 6 characters."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        with pytest.raises(ValidationError) as exc_info:
            VerificationCode(
                email="user@example.com",
                code="ABC12",  # Only 5 characters
                expires_at=expires_at,
                created_at=now,
            )

        assert "code" in str(exc_info.value).lower()

    def test_code_rejects_too_long(self):
        """Test that code rejects strings longer than 6 characters."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        with pytest.raises(ValidationError) as exc_info:
            VerificationCode(
                email="user@example.com",
                code="ABC1234",  # 7 characters
                expires_at=expires_at,
                created_at=now,
            )

        assert "code" in str(exc_info.value).lower()

    def test_code_rejects_special_characters(self):
        """Test that code rejects non-alphanumeric characters."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        invalid_codes = ["ABC@23", "AB-123", "A B123", "ABC.23"]

        for invalid_code in invalid_codes:
            with pytest.raises(ValidationError) as exc_info:
                VerificationCode(
                    email="user@example.com",
                    code=invalid_code,
                    expires_at=expires_at,
                    created_at=now,
                )
            assert "code" in str(exc_info.value).lower()

    def test_code_normalizes_to_uppercase(self):
        """Test that code normalizes to uppercase."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="abc123",  # Lowercase input
            expires_at=expires_at,
            created_at=now,
        )

        assert code.code == "ABC123"  # Should be normalized to uppercase

    def test_email_validation_accepts_valid_email(self):
        """Test that email validation accepts valid email addresses."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.com",
            "user123@test-domain.com",
        ]

        for valid_email in valid_emails:
            code = VerificationCode(
                email=valid_email,
                code="ABC123",
                expires_at=expires_at,
                created_at=now,
            )
            assert code.email == valid_email

    def test_email_validation_rejects_invalid_email(self):
        """Test that email validation rejects invalid email addresses."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user space@example.com",
        ]

        for invalid_email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                VerificationCode(
                    email=invalid_email,
                    code="ABC123",
                    expires_at=expires_at,
                    created_at=now,
                )
            assert "email" in str(exc_info.value).lower()

    def test_is_expired_when_expiration_in_past(self):
        """Test that is_expired returns True when expires_at is in the past."""
        now = datetime.now(UTC)
        past_date = now - timedelta(minutes=1)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            expires_at=past_date,
            created_at=now - timedelta(minutes=11),
        )

        assert code.is_expired() is True

    def test_is_not_expired_when_expiration_in_future(self):
        """Test that is_expired returns False when expires_at is in the future."""
        now = datetime.now(UTC)
        future_date = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            expires_at=future_date,
            created_at=now,
        )

        assert code.is_expired() is False

    def test_is_used_when_status_used(self):
        """Test that is_used returns True when status is USED."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.USED,
            expires_at=expires_at,
            created_at=now,
            used_at=now,
        )

        assert code.is_used() is True

    def test_is_not_used_when_status_pending(self):
        """Test that is_used returns False when status is PENDING."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.PENDING,
            expires_at=expires_at,
            created_at=now,
        )

        assert code.is_used() is False

    def test_is_not_used_when_status_expired(self):
        """Test that is_used returns False when status is EXPIRED."""
        now = datetime.now(UTC)
        past_date = now - timedelta(minutes=1)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.EXPIRED,
            expires_at=past_date,
            created_at=now - timedelta(minutes=11),
        )

        assert code.is_used() is False

    def test_is_valid_when_not_expired_and_not_used(self):
        """Test that is_valid returns True when code is not expired and not used."""
        now = datetime.now(UTC)
        future_date = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.PENDING,
            expires_at=future_date,
            created_at=now,
        )

        assert code.is_valid() is True

    def test_is_not_valid_when_expired(self):
        """Test that is_valid returns False when code is expired."""
        now = datetime.now(UTC)
        past_date = now - timedelta(minutes=1)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.PENDING,
            expires_at=past_date,
            created_at=now - timedelta(minutes=11),
        )

        assert code.is_valid() is False

    def test_is_not_valid_when_used(self):
        """Test that is_valid returns False when code is used."""
        now = datetime.now(UTC)
        future_date = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.USED,
            expires_at=future_date,
            created_at=now,
            used_at=now,
        )

        assert code.is_valid() is False

    def test_mark_as_used(self):
        """Test marking a pending code as used."""
        now = datetime.now(UTC)
        future_date = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.PENDING,
            expires_at=future_date,
            created_at=now,
            used_at=None,
        )

        assert code.status == VerificationCodeStatus.PENDING
        assert code.used_at is None

        code.mark_as_used()

        assert code.status == VerificationCodeStatus.USED
        assert code.used_at is not None
        # Should be set to current time (within 1 second tolerance)
        assert (datetime.now(UTC) - code.used_at).total_seconds() < 1

    def test_mark_as_expired(self):
        """Test marking a pending code as expired."""
        now = datetime.now(UTC)
        future_date = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            status=VerificationCodeStatus.PENDING,
            expires_at=future_date,
            created_at=now,
        )

        assert code.status == VerificationCodeStatus.PENDING

        code.mark_as_expired()

        assert code.status == VerificationCodeStatus.EXPIRED

    def test_verification_code_equality_based_on_id(self):
        """Test that verification code equality is based on ID."""
        entity_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code1 = VerificationCode(
            id=entity_id,
            email="user1@example.com",
            code="ABC123",
            expires_at=expires_at,
            created_at=now,
        )

        code2 = VerificationCode(
            id=entity_id,
            email="user2@example.com",
            code="XYZ789",
            expires_at=expires_at,
            created_at=now,
        )

        assert code1 == code2

    def test_verification_code_inequality_different_ids(self):
        """Test that verification codes with different IDs are not equal."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code1 = VerificationCode(
            email="user@example.com",
            code="ABC123",
            expires_at=expires_at,
            created_at=now,
        )

        code2 = VerificationCode(
            email="user@example.com",
            code="ABC123",
            expires_at=expires_at,
            created_at=now,
        )

        assert code1 != code2


class TestVerificationCodeType:
    """Test suite for VerificationCodeType enum and type field."""

    def test_verification_code_type_enum_values(self):
        """Test that VerificationCodeType has expected values."""
        assert VerificationCodeType.REGISTRATION.value == "registration"
        assert VerificationCodeType.INVITE.value == "invite"

    def test_verification_code_type_defaults_to_registration(self):
        """Test that code type defaults to REGISTRATION when not specified."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            expires_at=expires_at,
            created_at=now,
        )

        assert code.code_type == VerificationCodeType.REGISTRATION

    def test_verification_code_can_be_created_with_invite_type(self):
        """Test that verification code can be created with INVITE type."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=24)
        user_id = UserID(uuid4())

        code = VerificationCode(
            email="invited@example.com",
            code="XYZ789",
            code_type=VerificationCodeType.INVITE,
            user_id=user_id,
            expires_at=expires_at,
            created_at=now,
        )

        assert code.code_type == VerificationCodeType.INVITE
        assert code.user_id == user_id

    def test_user_id_defaults_to_none(self):
        """Test that user_id defaults to None for registration codes."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)

        code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            expires_at=expires_at,
            created_at=now,
        )

        assert code.user_id is None

    def test_invite_code_requires_user_id(self):
        """Test that invite codes should have a user_id set."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=24)
        user_id = UserID(uuid4())

        # Invite code with user_id
        code = VerificationCode(
            email="invited@example.com",
            code="ABC123",
            code_type=VerificationCodeType.INVITE,
            user_id=user_id,
            expires_at=expires_at,
            created_at=now,
        )

        assert code.code_type == VerificationCodeType.INVITE
        assert code.user_id == user_id
        assert code.user_id is not None
        assert code.user_id.uuid == user_id.uuid

    def test_is_invite_property(self):
        """Test is_invite property returns True for INVITE type."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=24)
        user_id = UserID(uuid4())

        invite_code = VerificationCode(
            email="invited@example.com",
            code="ABC123",
            code_type=VerificationCodeType.INVITE,
            user_id=user_id,
            expires_at=expires_at,
            created_at=now,
        )

        registration_code = VerificationCode(
            email="user@example.com",
            code="XYZ789",
            code_type=VerificationCodeType.REGISTRATION,
            expires_at=expires_at,
            created_at=now,
        )

        assert invite_code.is_invite is True
        assert registration_code.is_invite is False

    def test_is_registration_property(self):
        """Test is_registration property returns True for REGISTRATION type."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=10)
        user_id = UserID(uuid4())

        registration_code = VerificationCode(
            email="user@example.com",
            code="ABC123",
            code_type=VerificationCodeType.REGISTRATION,
            expires_at=expires_at,
            created_at=now,
        )

        invite_code = VerificationCode(
            email="invited@example.com",
            code="XYZ789",
            code_type=VerificationCodeType.INVITE,
            user_id=user_id,
            expires_at=expires_at,
            created_at=now,
        )

        assert registration_code.is_registration is True
        assert invite_code.is_registration is False
