"""Tests for NonceService."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.adapters.orm import IdentityORM, NonceORM
from leadr.auth.domain.nonce import NonceStatus
from leadr.auth.services.nonce_service import NonceService
from leadr.common.domain.ids import IdentityID


@pytest.mark.asyncio
class TestNonceService:
    """Test suite for NonceService."""

    async def test_generate_nonce_creates_nonce_with_default_ttl(
        self, db_session: AsyncSession, identity_orm
    ):
        """Test generating a nonce with default TTL."""

        # Generate nonce
        service = NonceService(db_session)
        nonce_value, expires_at = await service.generate_nonce(
            identity_id=IdentityID(identity_orm.id)
        )

        # Verify nonce was created
        assert nonce_value is not None
        assert len(nonce_value) == 36  # UUID string length

        # Verify expiry is approximately 60 seconds from now (default TTL)
        expected_expiry = datetime.now(UTC) + timedelta(seconds=60)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2  # Within 2 seconds tolerance

    async def test_generate_nonce_creates_nonce_with_custom_ttl(
        self, db_session: AsyncSession, identity_orm
    ):
        """Test generating a nonce with custom TTL."""

        # Generate nonce with 120 second TTL
        service = NonceService(db_session)
        nonce_value, expires_at = await service.generate_nonce(
            identity_id=IdentityID(identity_orm.id), ttl_seconds=120
        )

        # Verify expiry is approximately 120 seconds from now
        expected_expiry = datetime.now(UTC) + timedelta(seconds=120)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2

    async def test_generate_nonce_stores_in_database(self, db_session: AsyncSession, identity_orm):
        """Test that generated nonce is stored in database."""

        # Generate nonce
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(identity_id=IdentityID(identity_orm.id))

        # Verify nonce exists in database
        repository = service.repository
        nonce = await repository.get_by_nonce_value(nonce_value)

        assert nonce is not None
        assert nonce.nonce_value == nonce_value
        assert nonce.identity_id == IdentityID(identity_orm.id)
        assert nonce.status == NonceStatus.PENDING

    async def test_validate_and_consume_nonce_success(self, db_session: AsyncSession, identity_orm):
        """Test successfully validating and consuming a nonce."""

        # Generate nonce
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(identity_id=IdentityID(identity_orm.id))

        # Validate and consume
        result = await service.validate_and_consume_nonce(nonce_value, IdentityID(identity_orm.id))

        assert result is True

        # Verify nonce is marked as used
        repository = service.repository
        nonce = await repository.get_by_nonce_value(nonce_value)

        assert nonce is not None
        assert nonce.status == NonceStatus.USED
        assert nonce.used_at is not None

    async def test_validate_and_consume_nonce_not_found(
        self, db_session: AsyncSession, identity_orm
    ):
        """Test that validating unknown nonce raises ValueError."""

        # Try to validate unknown nonce
        service = NonceService(db_session)

        with pytest.raises(ValueError, match="Nonce not found"):
            await service.validate_and_consume_nonce("unknown-nonce", IdentityID(identity_orm.id))

    async def test_validate_and_consume_nonce_wrong_identity(
        self, db_session: AsyncSession, identity_orm, game_orm
    ):
        """Test that using nonce from different identity raises ValueError."""
        # Create second identity with different external_key
        from leadr.auth.adapters.orm import IdentityKindEnum

        identity2 = IdentityORM(
            id=uuid4(),
            game_id=game_orm.id,
            account_id=game_orm.account_id,
            kind=IdentityKindEnum.DEVICE,
            external_key="other_fingerprint_12345",
            display_name="Other Player",
        )
        db_session.add(identity2)
        await db_session.commit()

        # Generate nonce for identity1
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(identity_id=IdentityID(identity_orm.id))

        # Try to use nonce with identity2
        with pytest.raises(ValueError, match="Nonce does not belong to this identity"):
            await service.validate_and_consume_nonce(nonce_value, IdentityID(identity2.id))

    async def test_validate_and_consume_nonce_already_used(
        self, db_session: AsyncSession, identity_orm
    ):
        """Test that using nonce twice raises ValueError."""

        # Generate and use nonce
        service = NonceService(db_session)
        nonce_value, _ = await service.generate_nonce(identity_id=IdentityID(identity_orm.id))
        await service.validate_and_consume_nonce(nonce_value, IdentityID(identity_orm.id))

        # Try to use same nonce again
        with pytest.raises(ValueError, match="Nonce already used"):
            await service.validate_and_consume_nonce(nonce_value, IdentityID(identity_orm.id))

    async def test_validate_and_consume_nonce_expired(self, db_session: AsyncSession, identity_orm):
        """Test that using expired nonce raises ValueError."""

        # Create expired nonce directly in DB
        expired_nonce = NonceORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),  # Expired
            status="pending",
        )
        db_session.add(expired_nonce)
        await db_session.commit()

        # Try to use expired nonce
        service = NonceService(db_session)

        with pytest.raises(ValueError, match="Nonce expired"):
            await service.validate_and_consume_nonce(
                expired_nonce.nonce_value, IdentityID(identity_orm.id)
            )

    async def test_cleanup_expired_nonces_deletes_old_nonces(
        self, db_session: AsyncSession, identity_orm
    ):
        """Test that cleanup deletes old expired nonces."""

        # Create old expired nonce (expired 25 hours ago) - custom value
        old_nonce = NonceORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(hours=25),  # Custom
            status="pending",
        )
        db_session.add(old_nonce)

        # Create recent expired nonce (expired 30 minutes ago) - custom value
        recent_nonce = NonceORM(
            id=uuid4(),
            identity_id=identity_orm.id,
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(minutes=30),  # Custom
            status="pending",
        )
        db_session.add(recent_nonce)

        await db_session.commit()

        # Cleanup nonces older than 24 hours
        service = NonceService(db_session)
        deleted_count = await service.cleanup_expired_nonces(older_than_hours=24)

        # Should delete only the old nonce
        assert deleted_count == 1

        # Verify old nonce is gone
        repository = service.repository
        old_retrieved = await repository.get_by_id(old_nonce.id)
        assert old_retrieved is None

        # Verify recent nonce still exists
        recent_retrieved = await repository.get_by_id(recent_nonce.id)
        assert recent_retrieved is not None

    async def test_cleanup_expired_nonces_returns_zero_when_none_to_delete(
        self, db_session: AsyncSession
    ):
        """Test that cleanup returns 0 when there are no nonces to delete."""
        service = NonceService(db_session)
        deleted_count = await service.cleanup_expired_nonces(older_than_hours=24)

        assert deleted_count == 0

    async def test_multiple_identities_can_have_pending_nonces(
        self, db_session: AsyncSession, identity_orm, game_orm
    ):
        """Test that multiple identities can have pending nonces simultaneously."""
        # Create second identity with different external_key
        from leadr.auth.adapters.orm import IdentityKindEnum

        identity2 = IdentityORM(
            id=uuid4(),
            game_id=game_orm.id,
            account_id=game_orm.account_id,
            kind=IdentityKindEnum.DEVICE,
            external_key="other_fingerprint_12345",
            display_name="Other Player",
        )
        db_session.add(identity2)
        await db_session.commit()

        # Generate nonces for both identities
        service = NonceService(db_session)
        nonce1, _ = await service.generate_nonce(identity_id=IdentityID(identity_orm.id))
        nonce2, _ = await service.generate_nonce(identity_id=IdentityID(identity2.id))

        # Both nonces should be unique and valid
        assert nonce1 != nonce2

        # Each identity can use its own nonce
        result1 = await service.validate_and_consume_nonce(nonce1, IdentityID(identity_orm.id))
        result2 = await service.validate_and_consume_nonce(nonce2, IdentityID(identity2.id))

        assert result1 is True
        assert result2 is True
