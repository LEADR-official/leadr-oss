"""Tests for email domain models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from leadr.infra.email.domain.exceptions import EmailValidationError
from leadr.infra.email.domain.models import Email, EmailPriority, EmailStatus


class TestEmailStatus:
    """Test EmailStatus enum."""

    def test_has_expected_values(self):
        """Test that EmailStatus has all expected values."""
        assert EmailStatus.PENDING == "pending"
        assert EmailStatus.SENT == "sent"
        assert EmailStatus.DELIVERED == "delivered"
        assert EmailStatus.FAILED == "failed"


class TestEmailPriority:
    """Test EmailPriority enum."""

    def test_has_expected_values(self):
        """Test that EmailPriority has all expected values."""
        assert EmailPriority.LOW == "low"
        assert EmailPriority.NORMAL == "normal"
        assert EmailPriority.HIGH == "high"
        assert EmailPriority.URGENT == "urgent"


class TestEmailValidation:
    """Test Email validation logic."""

    def test_valid_email_addresses(self):
        """Test that valid email addresses are accepted."""
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.com",
            "user123@test-domain.co.uk",
            "first.last@subdomain.example.com",
        ]

        for email_addr in valid_emails:
            email = Email.create(
                to=email_addr,
                subject="Test",
                body="Test body",
            )
            assert email.to == email_addr

    def test_invalid_to_email(self):
        """Test that invalid to email is rejected."""
        with pytest.raises(EmailValidationError, match="Invalid email address"):
            Email.create(
                to="not-an-email",
                subject="Test",
                body="Test body",
            )

    def test_invalid_from_email(self):
        """Test that invalid from email is rejected."""
        with pytest.raises(EmailValidationError, match="Invalid from email address"):
            Email.create(
                to="user@example.com",
                subject="Test",
                body="Test body",
                from_email="not-an-email",
            )

    def test_invalid_reply_to_email(self):
        """Test that invalid reply_to email is rejected."""
        with pytest.raises(EmailValidationError, match="Invalid reply-to email address"):
            Email.create(
                to="user@example.com",
                subject="Test",
                body="Test body",
                reply_to="not-an-email",
            )

    def test_invalid_cc_email(self):
        """Test that invalid CC email is rejected."""
        with pytest.raises(EmailValidationError, match="Invalid CC email address"):
            Email.create(
                to="user@example.com",
                subject="Test",
                body="Test body",
                cc=["valid@example.com", "invalid"],
            )

    def test_invalid_bcc_email(self):
        """Test that invalid BCC email is rejected."""
        with pytest.raises(EmailValidationError, match="Invalid BCC email address"):
            Email.create(
                to="user@example.com",
                subject="Test",
                body="Test body",
                bcc=["valid@example.com", "invalid"],
            )

    def test_empty_subject_rejected(self):
        """Test that empty subject is rejected."""
        with pytest.raises(EmailValidationError, match="Subject cannot be empty"):
            Email.create(
                to="user@example.com",
                subject="",
                body="Test body",
            )

    def test_whitespace_only_subject_rejected(self):
        """Test that whitespace-only subject is rejected."""
        with pytest.raises(EmailValidationError, match="Subject cannot be empty"):
            Email.create(
                to="user@example.com",
                subject="   ",
                body="Test body",
            )

    def test_empty_body_rejected(self):
        """Test that empty body is rejected."""
        with pytest.raises(EmailValidationError, match="Body cannot be empty"):
            Email.create(
                to="user@example.com",
                subject="Test",
                body="",
            )

    def test_whitespace_only_body_rejected(self):
        """Test that whitespace-only body is rejected."""
        with pytest.raises(EmailValidationError, match="Body cannot be empty"):
            Email.create(
                to="user@example.com",
                subject="Test",
                body="   ",
            )

    def test_subject_trimmed(self):
        """Test that subject is trimmed of whitespace."""
        email = Email.create(
            to="user@example.com",
            subject="  Test Subject  ",
            body="Test body",
        )
        assert email.subject == "Test Subject"

    def test_body_trimmed(self):
        """Test that body is trimmed of whitespace."""
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="  Test body  ",
        )
        assert email.body == "Test body"


class TestEmailCreate:
    """Test Email.create factory method."""

    def test_create_minimal(self):
        """Test creating email with minimal required fields."""
        email = Email.create(
            to="user@example.com",
            subject="Test Subject",
            body="Test body content",
        )

        assert email.to == "user@example.com"
        assert email.subject == "Test Subject"
        assert email.body == "Test body content"
        assert email.from_email is None
        assert email.reply_to is None
        assert email.cc == []
        assert email.bcc == []
        assert email.priority == EmailPriority.NORMAL
        assert email.status == EmailStatus.PENDING
        assert email.template_data is None
        assert email.provider_message_id is None
        assert email.provider_response is None
        assert email.sent_at is None
        assert email.failed_at is None
        assert email.error_message is None

    def test_create_with_all_fields(self):
        """Test creating email with all fields."""
        template_data = {"name": "John", "code": "ABC123"}

        email = Email.create(
            to="user@example.com",
            subject="Test Subject",
            body="Test body",
            from_email="sender@example.com",
            reply_to="reply@example.com",
            cc=["cc1@example.com", "cc2@example.com"],
            bcc=["bcc@example.com"],
            priority=EmailPriority.HIGH,
            template_data=template_data,
        )

        assert email.to == "user@example.com"
        assert email.subject == "Test Subject"
        assert email.body == "Test body"
        assert email.from_email == "sender@example.com"
        assert email.reply_to == "reply@example.com"
        assert email.cc == ["cc1@example.com", "cc2@example.com"]
        assert email.bcc == ["bcc@example.com"]
        assert email.priority == EmailPriority.HIGH
        assert email.template_data == template_data

    def test_create_generates_id(self):
        """Test that create generates a unique ID."""
        email1 = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )
        email2 = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        assert email1.id != email2.id

    def test_create_sets_timestamps(self):
        """Test that create sets created_at and updated_at."""
        before = datetime.now(UTC)
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )
        after = datetime.now(UTC)

        assert before <= email.created_at <= after
        assert before <= email.updated_at <= after


class TestEmailStatusTransitions:
    """Test Email status transition methods."""

    def test_mark_as_sent(self):
        """Test marking email as sent."""
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        provider_response = {"id": "msg-123", "status": "queued"}
        before = datetime.now(UTC)
        email.mark_as_sent("msg-123", provider_response)
        after = datetime.now(UTC)

        assert email.status == EmailStatus.SENT
        assert email.provider_message_id == "msg-123"
        assert email.provider_response == provider_response
        assert email.sent_at is not None
        assert before <= email.sent_at <= after
        assert before <= email.updated_at <= after

    def test_mark_as_failed_with_response(self):
        """Test marking email as failed with provider response."""
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        provider_response = {"error": "Invalid recipient"}
        before = datetime.now(UTC)
        email.mark_as_failed("Failed to send", provider_response)
        after = datetime.now(UTC)

        assert email.status == EmailStatus.FAILED
        assert email.error_message == "Failed to send"
        assert email.provider_response == provider_response
        assert email.failed_at is not None
        assert before <= email.failed_at <= after
        assert before <= email.updated_at <= after

    def test_mark_as_failed_without_response(self):
        """Test marking email as failed without provider response."""
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        email.mark_as_failed("Network error")

        assert email.status == EmailStatus.FAILED
        assert email.error_message == "Network error"
        assert email.provider_response is None

    def test_mark_as_delivered(self):
        """Test marking email as delivered."""
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        # First mark as sent
        email.mark_as_sent("msg-123", {"id": "msg-123"})

        # Then mark as delivered
        before = datetime.now(UTC)
        email.mark_as_delivered()
        after = datetime.now(UTC)

        assert email.status == EmailStatus.DELIVERED
        assert before <= email.updated_at <= after


class TestEmailEntity:
    """Test Email entity base functionality."""

    def test_email_is_immutable_id(self):
        """Test that email ID is immutable."""
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        with pytest.raises(ValidationError):
            email.id = "new-id"  # type: ignore[misc]

    def test_email_allows_status_updates(self):
        """Test that email status can be updated."""
        email = Email.create(
            to="user@example.com",
            subject="Test",
            body="Test body",
        )

        assert email.status == EmailStatus.PENDING
        email.status = EmailStatus.SENT
        assert email.status == EmailStatus.SENT
