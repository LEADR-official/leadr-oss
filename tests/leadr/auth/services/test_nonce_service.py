"""Tests for NonceService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.auth.domain.nonce import Nonce, NonceStatus
from leadr.auth.services.nonce_service import NonceService
from leadr.common.domain.ids import IdentityID


@pytest.fixture
def service(mock_session):
    """Create NonceService with mock repository."""
    return NonceService(mock_session, repository=MagicMock())


@pytest.mark.asyncio
class TestNonceService:
    """Test suite for NonceService."""

    async def test_generate_nonce_creates_nonce_with_default_ttl(self, service):
        """Test generating a nonce with default TTL."""
        identity_id = IdentityID(uuid4())

        # Mock repository create
        created_nonce = None

        async def capture_nonce(nonce):
            nonlocal created_nonce
            created_nonce = nonce
            return nonce

        service.repository.create = AsyncMock(side_effect=capture_nonce)

        # Generate nonce
        nonce_value, expires_at = await service.generate_nonce(identity_id=identity_id)

        # Verify nonce was created
        assert nonce_value is not None
        assert len(nonce_value) == 36  # UUID string length

        # Verify expiry is approximately 60 seconds from now (default TTL)
        expected_expiry = datetime.now(UTC) + timedelta(seconds=60)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2  # Within 2 seconds tolerance

        # Verify repository.create was called
        service.repository.create.assert_called_once()
        assert created_nonce is not None
        assert created_nonce.identity_id == identity_id
        assert created_nonce.status == NonceStatus.PENDING

    async def test_generate_nonce_creates_nonce_with_custom_ttl(self, service):
        """Test generating a nonce with custom TTL."""
        identity_id = IdentityID(uuid4())

        # Mock repository create
        service.repository.create = AsyncMock(return_value=MagicMock())

        # Generate nonce with 120 second TTL
        nonce_value, expires_at = await service.generate_nonce(
            identity_id=identity_id, ttl_seconds=120
        )

        # Verify expiry is approximately 120 seconds from now
        expected_expiry = datetime.now(UTC) + timedelta(seconds=120)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 2

    async def test_generate_nonce_stores_nonce(self, service):
        """Test that generated nonce is stored via repository."""
        identity_id = IdentityID(uuid4())

        # Mock repository create
        created_nonce = None

        async def capture_nonce(nonce):
            nonlocal created_nonce
            created_nonce = nonce
            return nonce

        service.repository.create = AsyncMock(side_effect=capture_nonce)

        # Generate nonce
        nonce_value, _ = await service.generate_nonce(identity_id=identity_id)

        # Verify repository.create was called with correct nonce
        service.repository.create.assert_called_once()
        assert created_nonce is not None
        assert created_nonce.nonce_value == nonce_value
        assert created_nonce.identity_id == identity_id
        assert created_nonce.status == NonceStatus.PENDING

    async def test_validate_and_consume_nonce_success(self, service):
        """Test successfully validating and consuming a nonce."""
        identity_id = IdentityID(uuid4())
        nonce_value = str(uuid4())

        # Create valid nonce
        nonce = Nonce(
            identity_id=identity_id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.PENDING,
        )

        # Mock repository methods
        service.repository.get_by_nonce_value = AsyncMock(return_value=nonce)
        service.repository.update = AsyncMock(return_value=nonce)

        # Validate and consume
        result = await service.validate_and_consume_nonce(nonce_value, identity_id)

        assert result is True

        # Verify nonce was marked as used
        assert nonce.status == NonceStatus.USED
        assert nonce.used_at is not None

        # Verify repository methods were called
        service.repository.get_by_nonce_value.assert_called_once_with(nonce_value)
        service.repository.update.assert_called_once_with(nonce)

    async def test_validate_and_consume_nonce_not_found(self, service):
        """Test that validating unknown nonce raises ValueError."""
        identity_id = IdentityID(uuid4())

        # Mock repository to return None (nonce not found)
        service.repository.get_by_nonce_value = AsyncMock(return_value=None)

        # Try to validate unknown nonce
        with pytest.raises(ValueError, match="Nonce not found"):
            await service.validate_and_consume_nonce("unknown-nonce", identity_id)

    async def test_validate_and_consume_nonce_wrong_identity(self, service):
        """Test that using nonce from different identity raises ValueError."""
        identity1_id = IdentityID(uuid4())
        identity2_id = IdentityID(uuid4())
        nonce_value = str(uuid4())

        # Create nonce for identity1
        nonce = Nonce(
            identity_id=identity1_id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.PENDING,
        )

        # Mock repository
        service.repository.get_by_nonce_value = AsyncMock(return_value=nonce)

        # Try to use nonce with identity2
        with pytest.raises(ValueError, match="Nonce does not belong to this identity"):
            await service.validate_and_consume_nonce(nonce_value, identity2_id)

    async def test_validate_and_consume_nonce_already_used(self, service):
        """Test that using nonce twice raises ValueError."""
        identity_id = IdentityID(uuid4())
        nonce_value = str(uuid4())

        # Create used nonce
        nonce = Nonce(
            identity_id=identity_id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.USED,
            used_at=datetime.now(UTC),
        )

        # Mock repository
        service.repository.get_by_nonce_value = AsyncMock(return_value=nonce)

        # Try to use already used nonce
        with pytest.raises(ValueError, match="Nonce already used"):
            await service.validate_and_consume_nonce(nonce_value, identity_id)

    async def test_validate_and_consume_nonce_expired(self, service):
        """Test that using expired nonce raises ValueError."""
        identity_id = IdentityID(uuid4())
        nonce_value = str(uuid4())

        # Create expired nonce
        nonce = Nonce(
            identity_id=identity_id,
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),  # Expired
            status=NonceStatus.PENDING,
        )

        # Mock repository
        service.repository.get_by_nonce_value = AsyncMock(return_value=nonce)

        # Try to use expired nonce
        with pytest.raises(ValueError, match="Nonce expired"):
            await service.validate_and_consume_nonce(nonce_value, identity_id)

    async def test_cleanup_expired_nonces_deletes_old_nonces(self, service):
        """Test that cleanup deletes old expired nonces."""
        # Mock repository cleanup method
        service.repository.cleanup_expired_nonces = AsyncMock(return_value=1)

        # Cleanup nonces older than 24 hours
        deleted_count = await service.cleanup_expired_nonces(older_than_hours=24)

        # Should return deleted count
        assert deleted_count == 1

        # Verify repository method was called with correct cutoff
        service.repository.cleanup_expired_nonces.assert_called_once()
        call_args = service.repository.cleanup_expired_nonces.call_args[0]
        cutoff = call_args[0]

        # Verify cutoff is approximately 24 hours ago
        expected_cutoff = datetime.now(UTC) - timedelta(hours=24)
        time_diff = abs((cutoff - expected_cutoff).total_seconds())
        assert time_diff < 2  # Within 2 seconds tolerance

    async def test_cleanup_expired_nonces_returns_zero_when_none_to_delete(self, service):
        """Test that cleanup returns 0 when there are no nonces to delete."""
        # Mock repository cleanup method to return 0
        service.repository.cleanup_expired_nonces = AsyncMock(return_value=0)

        deleted_count = await service.cleanup_expired_nonces(older_than_hours=24)

        assert deleted_count == 0

    async def test_multiple_identities_can_have_pending_nonces(self, service):
        """Test that multiple identities can have pending nonces simultaneously."""
        identity1_id = IdentityID(uuid4())
        identity2_id = IdentityID(uuid4())

        # Mock repository methods for generation
        create_calls = []

        async def capture_create(nonce):
            create_calls.append(nonce)
            return nonce

        service.repository.create = AsyncMock(side_effect=capture_create)

        # Generate nonces for both identities
        generated_nonce1, _ = await service.generate_nonce(identity_id=identity1_id)
        generated_nonce2, _ = await service.generate_nonce(identity_id=identity2_id)

        # Both nonces should be unique
        assert generated_nonce1 != generated_nonce2

        # Mock repository methods for validation
        async def get_by_nonce_value(value):
            if value == generated_nonce1:
                return create_calls[0]
            elif value == generated_nonce2:
                return create_calls[1]
            return None

        service.repository.get_by_nonce_value = AsyncMock(side_effect=get_by_nonce_value)
        service.repository.update = AsyncMock(side_effect=lambda n: n)

        # Each identity can use its own nonce
        result1 = await service.validate_and_consume_nonce(generated_nonce1, identity1_id)
        result2 = await service.validate_and_consume_nonce(generated_nonce2, identity2_id)

        assert result1 is True
        assert result2 is True
