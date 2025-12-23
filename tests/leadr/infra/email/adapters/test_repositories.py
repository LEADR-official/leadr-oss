"""Tests for email repository."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
from leadr.infra.email.adapters.repositories import EmailRepository
from leadr.infra.email.domain.models import Email, EmailPriority, EmailStatus


@pytest.mark.asyncio
class TestEmailRepository:
    """Test EmailRepository."""

    async def test_create_email(self, db_session: AsyncSession):
        """Test creating an email in the database."""
        repository = EmailRepository(db_session)

        email = Email.create(
            to="test@example.com",
            subject="Test Subject",
            body="Test body content",
            priority=EmailPriority.HIGH,
        )

        created = await repository.create(email)
        await db_session.commit()

        assert created.id == email.id
        assert created.to == "test@example.com"
        assert created.subject == "Test Subject"
        assert created.body == "Test body content"
        assert created.priority == EmailPriority.HIGH
        assert created.status == EmailStatus.PENDING

    async def test_get_by_id(self, db_session: AsyncSession):
        """Test retrieving email by ID."""
        repository = EmailRepository(db_session)

        email = Email.create(
            to="test@example.com",
            subject="Test",
            body="Test body",
        )

        await repository.create(email)
        await db_session.commit()

        retrieved = await repository.get_by_id(email.id.uuid)
        assert retrieved is not None
        assert retrieved.id == email.id
        assert retrieved.to == "test@example.com"

    async def test_get_by_id_nonexistent(self, db_session: AsyncSession):
        """Test retrieving nonexistent email returns None."""

        repository = EmailRepository(db_session)

        retrieved = await repository.get_by_id(uuid4())
        assert retrieved is None

    async def test_update_email(self, db_session: AsyncSession):
        """Test updating an email."""
        repository = EmailRepository(db_session)

        email = Email.create(
            to="test@example.com",
            subject="Test",
            body="Test body",
        )

        await repository.create(email)
        await db_session.commit()

        # Update status
        email.mark_as_sent("msg-123", {"id": "msg-123"})
        updated = await repository.update(email)
        await db_session.commit()

        assert updated.status == EmailStatus.SENT
        assert updated.provider_message_id == "msg-123"

    async def test_filter_by_to(self, db_session: AsyncSession):
        """Test filtering emails by recipient."""
        repository = EmailRepository(db_session)

        # Create emails for different recipients
        email1 = Email.create(to="user1@example.com", subject="Test 1", body="Body 1")
        email2 = Email.create(to="user2@example.com", subject="Test 2", body="Body 2")
        email3 = Email.create(to="user1@example.com", subject="Test 3", body="Body 3")

        await repository.create(email1)
        await repository.create(email2)
        await repository.create(email3)
        await db_session.commit()

        # Filter by user1
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(to="user1@example.com", pagination=pagination)
        assert len(result.items) == 2
        assert all(e.to == "user1@example.com" for e in result.items)

    async def test_filter_by_status(self, db_session: AsyncSession):
        """Test filtering emails by status."""
        repository = EmailRepository(db_session)

        # Create emails with different statuses
        email1 = Email.create(to="user@example.com", subject="Test 1", body="Body 1")
        email2 = Email.create(to="user@example.com", subject="Test 2", body="Body 2")
        email3 = Email.create(to="user@example.com", subject="Test 3", body="Body 3")

        email2.mark_as_sent("msg-123", {"id": "msg-123"})

        await repository.create(email1)
        await repository.create(email2)
        await repository.create(email3)
        await db_session.commit()

        pagination = PaginationParams(cursor=None, limit=100, sort=None)

        # Filter by PENDING
        pending = await repository.filter(status=EmailStatus.PENDING, pagination=pagination)
        assert len(pending.items) == 2

        # Filter by SENT
        sent = await repository.filter(status=EmailStatus.SENT, pagination=pagination)
        assert len(sent.items) == 1
        assert sent.items[0].id == email2.id

    async def test_filter_no_results(self, db_session: AsyncSession):
        """Test filtering with no matching results."""
        repository = EmailRepository(db_session)

        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(to="nonexistent@example.com", pagination=pagination)
        assert result.items == []

    async def test_filter_with_account_id_ignored(self, db_session: AsyncSession):
        """Test that account_id parameter is ignored (emails are top-level)."""
        repository = EmailRepository(db_session)

        email = Email.create(to="user@example.com", subject="Test", body="Body")
        await repository.create(email)
        await db_session.commit()

        # account_id should be ignored
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await repository.filter(account_id=uuid4(), pagination=pagination)
        assert len(result.items) == 1

    async def test_roundtrip_with_all_fields(self, db_session: AsyncSession):
        """Test roundtrip with all email fields populated."""
        repository = EmailRepository(db_session)

        email = Email.create(
            to="user@example.com",
            subject="Test Subject",
            body="Test body",
            from_email="sender@example.com",
            reply_to="reply@example.com",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            priority=EmailPriority.URGENT,
            template_data={"key": "value"},
        )

        email.mark_as_sent("msg-456", {"response": "ok"})

        await repository.create(email)
        await db_session.commit()

        retrieved = await repository.get_by_id(email.id.uuid)

        assert retrieved is not None
        assert retrieved.to == "user@example.com"
        assert retrieved.subject == "Test Subject"
        assert retrieved.body == "Test body"
        assert retrieved.from_email == "sender@example.com"
        assert retrieved.reply_to == "reply@example.com"
        assert retrieved.cc == ["cc@example.com"]
        assert retrieved.bcc == ["bcc@example.com"]
        assert retrieved.priority == EmailPriority.URGENT
        assert retrieved.template_data == {"key": "value"}
        assert retrieved.status == EmailStatus.SENT
        assert retrieved.provider_message_id == "msg-456"
        assert retrieved.provider_response == {"response": "ok"}
        assert retrieved.sent_at is not None
