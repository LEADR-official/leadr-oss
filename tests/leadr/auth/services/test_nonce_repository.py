"""Tests for NonceRepository."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.adapters.orm import DeviceORM, NonceORM
from leadr.auth.domain.nonce import Nonce, NonceStatus
from leadr.auth.services.repositories import NonceRepository
from leadr.common.domain.ids import DeviceID


@pytest.mark.asyncio
class TestNonceRepository:
    """Test suite for NonceRepository."""

    async def test_create_nonce(self, db_session: AsyncSession, device_orm: DeviceORM):
        """Test creating a nonce via repository."""
        # Create nonce entity
        nonce = Nonce(
            device_id=DeviceID(device_orm.id),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.PENDING,
        )

        # Create via repository
        repository = NonceRepository(db_session)
        created_nonce = await repository.create(nonce)

        assert created_nonce.id == nonce.id
        assert created_nonce.device_id == device_orm.id
        assert created_nonce.nonce_value == nonce.nonce_value
        assert created_nonce.status == NonceStatus.PENDING

    async def test_get_by_id(self, db_session: AsyncSession, nonce_orm: NonceORM):
        """Test getting a nonce by ID."""
        # Get via repository
        repository = NonceRepository(db_session)
        retrieved = await repository.get_by_id(nonce_orm.id)

        assert retrieved is not None
        assert retrieved.id == nonce_orm.id
        assert retrieved.device_id == nonce_orm.device_id
        assert retrieved.nonce_value == nonce_orm.nonce_value

    async def test_get_by_nonce_value_returns_nonce(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test getting a nonce by nonce_value."""
        # Create nonce
        nonce_value = str(uuid4())
        nonce_orm = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status="pending",
        )
        db_session.add(nonce_orm)
        await db_session.commit()

        # Get by nonce_value
        repository = NonceRepository(db_session)
        retrieved = await repository.get_by_nonce_value(nonce_value)

        assert retrieved is not None
        assert retrieved.nonce_value == nonce_value
        assert retrieved.device_id == device_orm.id
        assert retrieved.status == NonceStatus.PENDING

    async def test_get_by_nonce_value_returns_none_for_unknown_value(
        self, db_session: AsyncSession
    ):
        """Test that get_by_nonce_value returns None for unknown nonce value."""
        repository = NonceRepository(db_session)
        retrieved = await repository.get_by_nonce_value("unknown-nonce-value")

        assert retrieved is None

    async def test_get_by_nonce_value_excludes_soft_deleted(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test that get_by_nonce_value excludes soft-deleted nonces."""
        # Create soft-deleted nonce
        nonce_value = str(uuid4())
        nonce_orm = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status="pending",
            deleted_at=datetime.now(UTC),  # Soft deleted
        )
        db_session.add(nonce_orm)
        await db_session.commit()

        # Should not find soft-deleted nonce
        repository = NonceRepository(db_session)
        retrieved = await repository.get_by_nonce_value(nonce_value)

        assert retrieved is None

    async def test_update_nonce(self, db_session: AsyncSession, device_orm: DeviceORM):
        """Test updating a nonce."""
        # Create nonce
        nonce = Nonce(
            device_id=DeviceID(device_orm.id),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.PENDING,
        )

        repository = NonceRepository(db_session)
        created_nonce = await repository.create(nonce)

        # Update nonce
        created_nonce.mark_used()
        updated_nonce = await repository.update(created_nonce)

        assert updated_nonce.status == NonceStatus.USED
        assert updated_nonce.used_at is not None

    async def test_cleanup_expired_nonces_deletes_old_expired(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test that cleanup_expired_nonces deletes old expired nonces."""
        # Create old expired nonce (expired 2 hours ago)
        old_expired_nonce = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=2),
            status="pending",
        )
        db_session.add(old_expired_nonce)

        # Create recent expired nonce (expired 30 seconds ago)
        recent_expired_nonce = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=30),
            status="pending",
        )
        db_session.add(recent_expired_nonce)

        # Create valid nonce
        valid_nonce = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status="pending",
        )
        db_session.add(valid_nonce)

        await db_session.commit()

        # Cleanup nonces expired before 1 hour ago
        repository = NonceRepository(db_session)
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        deleted_count = await repository.cleanup_expired_nonces(cutoff)

        # Should delete only the old expired nonce
        assert deleted_count == 1

        # Verify old nonce is gone
        old_retrieved = await repository.get_by_id(old_expired_nonce.id)
        assert old_retrieved is None

        # Verify recent expired nonce still exists
        recent_retrieved = await repository.get_by_id(recent_expired_nonce.id)
        assert recent_retrieved is not None

        # Verify valid nonce still exists
        valid_retrieved = await repository.get_by_id(valid_nonce.id)
        assert valid_retrieved is not None

    async def test_cleanup_expired_nonces_only_deletes_pending(
        self, db_session: AsyncSession, device_orm: DeviceORM
    ):
        """Test that cleanup only deletes nonces with PENDING status."""
        # Create old expired pending nonce
        pending_nonce = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=2),
            status="pending",
        )
        db_session.add(pending_nonce)

        # Create old expired used nonce
        used_nonce = NonceORM(
            id=uuid4(),
            device_id=device_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=2),
            status="used",
            used_at=datetime.now(UTC) - timedelta(hours=2),
        )
        db_session.add(used_nonce)

        await db_session.commit()

        # Cleanup nonces
        repository = NonceRepository(db_session)
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        deleted_count = await repository.cleanup_expired_nonces(cutoff)

        # Should delete only the pending nonce
        assert deleted_count == 1

        # Verify pending nonce is gone
        pending_retrieved = await repository.get_by_id(pending_nonce.id)
        assert pending_retrieved is None

        # Verify used nonce still exists (not deleted)
        used_retrieved = await repository.get_by_id(used_nonce.id)
        assert used_retrieved is not None

    async def test_cleanup_expired_nonces_returns_zero_when_none_to_delete(
        self, db_session: AsyncSession
    ):
        """Test that cleanup returns 0 when there are no nonces to delete."""
        repository = NonceRepository(db_session)
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        deleted_count = await repository.cleanup_expired_nonces(cutoff)

        assert deleted_count == 0
