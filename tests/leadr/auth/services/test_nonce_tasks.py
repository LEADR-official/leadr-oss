"""Tests for nonce background tasks."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.adapters.orm import NonceORM
from leadr.auth.services.nonce_service import NonceService
from leadr.auth.services.nonce_tasks import cleanup_expired_nonces


@pytest.mark.asyncio
class TestCleanupExpiredNonces:
    """Test suite for cleanup_expired_nonces background task."""

    async def test_cleanup_removes_expired_pending_nonces(
        self, db_session: AsyncSession, identity_orm
    ):
        """Test that expired pending nonces are deleted."""

        # Create expired pending nonce (expired 1 hour ago) - custom value
        nonce_id = uuid4()
        expired_nonce = NonceORM(
            id=nonce_id,
            identity_id=identity_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Custom
            status="pending",
        )
        db_session.add(expired_nonce)
        await db_session.commit()

        # Run cleanup using the service directly (same session as test)
        service = NonceService(db_session)
        deleted_count = await service.cleanup_expired_nonces(older_than_hours=0)

        # Verify nonce was deleted
        assert deleted_count == 1

        # Verify nonce no longer exists in database
        result = await db_session.execute(select(NonceORM).where(NonceORM.id == nonce_id))
        assert result.scalar_one_or_none() is None

    async def test_cleanup_keeps_valid_pending_nonces(self, db_session: AsyncSession, identity_orm):
        """Test that valid (not expired) pending nonces are kept."""
        # Create valid pending nonce (expires in 1 hour) - custom value
        valid_nonce = NonceORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(hours=1),  # Custom
            status="pending",
        )
        db_session.add(valid_nonce)
        await db_session.commit()

        # Mock create_session to return async context manager yielding our test session
        @asynccontextmanager
        async def mock_create_session():
            yield db_session

        with patch("leadr.auth.services.nonce_tasks.create_session", mock_create_session):
            # Run cleanup task
            await cleanup_expired_nonces()

        # Verify nonce still exists
        await db_session.refresh(valid_nonce)
        assert valid_nonce.status == "pending"

    async def test_cleanup_keeps_used_nonces(self, db_session: AsyncSession, identity_orm):
        """Test that used nonces are kept even if expired (for audit)."""
        # Create used nonce that expired 1 hour ago - custom values
        used_nonce = NonceORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Custom
            status="used",  # Custom
            used_at=datetime.now(UTC) - timedelta(minutes=30),  # Custom
        )
        db_session.add(used_nonce)
        await db_session.commit()

        # Mock create_session to return async context manager yielding our test session
        @asynccontextmanager
        async def mock_create_session():
            yield db_session

        with patch("leadr.auth.services.nonce_tasks.create_session", mock_create_session):
            # Run cleanup task
            await cleanup_expired_nonces()

        # Verify used nonce still exists
        await db_session.refresh(used_nonce)
        assert used_nonce.status == "used"

    async def test_cleanup_handles_no_expired_nonces(self, db_session: AsyncSession):
        """Test that cleanup task handles case with no expired nonces gracefully."""
        # No setup needed - empty database

        # Mock create_session to return async context manager yielding our test session
        @asynccontextmanager
        async def mock_create_session():
            yield db_session

        with patch("leadr.auth.services.nonce_tasks.create_session", mock_create_session):
            # Run cleanup task - should not raise any errors
            await cleanup_expired_nonces()

        # Task should complete without errors

    async def test_cleanup_handles_operational_error(self):
        """Test that cleanup handles OperationalError gracefully without raising."""
        mock_session = MagicMock()

        @asynccontextmanager
        async def mock_create_session():
            yield mock_session

        mock_nonce_service = MagicMock()
        mock_nonce_service.cleanup_expired_nonces = AsyncMock(
            side_effect=OperationalError("statement", {}, Exception("connection failed"))
        )

        with (
            patch("leadr.auth.services.nonce_tasks.create_session", mock_create_session),
            patch("leadr.auth.services.nonce_tasks.NonceService", return_value=mock_nonce_service),
        ):
            # Should not raise - error is handled internally
            await cleanup_expired_nonces()

        mock_nonce_service.cleanup_expired_nonces.assert_awaited_once()

    async def test_cleanup_handles_dbapi_error(self):
        """Test that cleanup handles DBAPIError gracefully without raising."""
        mock_session = MagicMock()

        @asynccontextmanager
        async def mock_create_session():
            yield mock_session

        mock_nonce_service = MagicMock()
        mock_nonce_service.cleanup_expired_nonces = AsyncMock(
            side_effect=DBAPIError("statement", {}, Exception("db error"))
        )

        with (
            patch("leadr.auth.services.nonce_tasks.create_session", mock_create_session),
            patch("leadr.auth.services.nonce_tasks.NonceService", return_value=mock_nonce_service),
        ):
            # Should not raise - error is handled internally
            await cleanup_expired_nonces()

        mock_nonce_service.cleanup_expired_nonces.assert_awaited_once()

    async def test_cleanup_handles_unexpected_error(self):
        """Test that cleanup handles unexpected exceptions gracefully without raising."""
        mock_session = MagicMock()

        @asynccontextmanager
        async def mock_create_session():
            yield mock_session

        mock_nonce_service = MagicMock()
        mock_nonce_service.cleanup_expired_nonces = AsyncMock(
            side_effect=RuntimeError("unexpected error")
        )

        with (
            patch("leadr.auth.services.nonce_tasks.create_session", mock_create_session),
            patch("leadr.auth.services.nonce_tasks.NonceService", return_value=mock_nonce_service),
        ):
            # Should not raise - error is handled internally
            await cleanup_expired_nonces()

        mock_nonce_service.cleanup_expired_nonces.assert_awaited_once()

    async def test_cleanup_logs_when_nonces_deleted(self):
        """Test that cleanup logs success message when nonces are deleted."""
        mock_session = MagicMock()

        @asynccontextmanager
        async def mock_create_session():
            yield mock_session

        mock_nonce_service = MagicMock()
        mock_nonce_service.cleanup_expired_nonces = AsyncMock(return_value=5)

        with (
            patch("leadr.auth.services.nonce_tasks.create_session", mock_create_session),
            patch("leadr.auth.services.nonce_tasks.NonceService", return_value=mock_nonce_service),
            patch("leadr.auth.services.nonce_tasks.logger") as mock_logger,
        ):
            await cleanup_expired_nonces()

        # Verify info log was called with the count
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "5" in str(call_args) or 5 in call_args[0]
