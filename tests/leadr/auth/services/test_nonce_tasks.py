"""Tests for nonce background tasks."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import DeviceORM, NonceORM
from leadr.auth.services.nonce_tasks import cleanup_expired_nonces
from leadr.common.domain.ids import NonceID
from leadr.games.adapters.orm import GameORM


@pytest.mark.asyncio
class TestCleanupExpiredNonces:
    """Test suite for cleanup_expired_nonces background task."""

    async def test_cleanup_removes_expired_pending_nonces(self, db_session: AsyncSession):
        """Test that expired pending nonces are deleted."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=account.id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Create expired pending nonce (expired 1 hour ago)
        nonce_id = NonceID(uuid4())
        expired_nonce = NonceORM(
            id=nonce_id,
            device_id=device.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            status="pending",
        )
        db_session.add(expired_nonce)
        await db_session.commit()

        # Run cleanup using the service directly (same session as test)
        from leadr.auth.services.nonce_service import NonceService

        service = NonceService(db_session)
        deleted_count = await service.cleanup_expired_nonces(older_than_hours=0)

        # Verify nonce was deleted
        assert deleted_count == 1

        # Verify nonce no longer exists in database
        result = await db_session.execute(select(NonceORM).where(NonceORM.id == nonce_id))
        assert result.scalar_one_or_none() is None

    async def test_cleanup_keeps_valid_pending_nonces(self, db_session: AsyncSession):
        """Test that valid (not expired) pending nonces are kept."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=account.id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Create valid pending nonce (expires in 1 hour)
        valid_nonce = NonceORM(
            id=uuid4(),
            device_id=device.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            status="pending",
        )
        db_session.add(valid_nonce)
        await db_session.commit()

        # Run cleanup task
        await cleanup_expired_nonces()

        # Verify nonce still exists
        await db_session.refresh(valid_nonce)
        assert valid_nonce.status == "pending"

    async def test_cleanup_keeps_used_nonces(self, db_session: AsyncSession):
        """Test that used nonces are kept even if expired (for audit)."""
        # Create account, game, and device
        account = AccountORM(
            id=uuid4(),
            name="Test Account",
            slug="test-account",
        )
        db_session.add(account)
        await db_session.commit()

        game = GameORM(
            id=uuid4(),
            account_id=account.id,
            name="Test Game",
        )
        db_session.add(game)
        await db_session.commit()

        device = DeviceORM(
            id=uuid4(),
            game_id=game.id,
            device_id="test-device",
            account_id=account.id,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        db_session.add(device)
        await db_session.commit()

        # Create used nonce that expired 1 hour ago
        used_nonce = NonceORM(
            id=uuid4(),
            device_id=device.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            status="used",
            used_at=datetime.now(UTC) - timedelta(minutes=30),
        )
        db_session.add(used_nonce)
        await db_session.commit()

        # Run cleanup task
        await cleanup_expired_nonces()

        # Verify used nonce still exists
        await db_session.refresh(used_nonce)
        assert used_nonce.status == "used"

    async def test_cleanup_handles_no_expired_nonces(self, db_session: AsyncSession):
        """Test that cleanup task handles case with no expired nonces gracefully."""
        # No setup needed - empty database

        # Run cleanup task - should not raise any errors
        await cleanup_expired_nonces()

        # Task should complete without errors
