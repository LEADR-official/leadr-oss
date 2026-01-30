"""Tests for APIKey service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.auth.domain.api_key import APIKeyStatus
from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, APIKeyID, UserID
from leadr.common.domain.pagination_result import PaginatedResult


@pytest.fixture
def mock_session():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def service(mock_session):
    """API key service with mocked repository."""
    return APIKeyService(mock_session, repository=MagicMock())


@pytest.mark.asyncio
class TestAPIKeyService:
    """Test suite for APIKey service."""

    async def test_create_api_key(self, service):
        """Test creating an API key with automatic generation and hashing."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key via service
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            user_id=user_id,
            name="Production Key",
            expires_at=None,
        )

        # Verify key was created
        assert api_key.account_id == account_id
        assert api_key.user_id == user_id
        assert api_key.name == "Production Key"
        assert api_key.status == APIKeyStatus.ACTIVE
        assert api_key.key_hash != ""
        assert api_key.key_prefix.startswith("ldr_")
        assert len(api_key.key_prefix) > 10  # Should have enough entropy

        # Verify plain key was returned
        assert plain_key.startswith("ldr_")
        assert len(plain_key) > 36
        assert plain_key != api_key.key_hash  # Should not be the same

        # Verify prefix matches the start of plain key
        assert plain_key.startswith(api_key.key_prefix)

        # Verify repository.create was called
        service.repository.create.assert_called_once()

    async def test_create_api_key_with_expiration(self, service):
        """Test creating an API key with an expiration date."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=90)

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key with expiration
        api_key, _ = await service.create_api_key(
            account_id=account_id,
            user_id=user_id,
            name="Temporary Key",
            expires_at=expires_at,
        )

        assert api_key.expires_at == expires_at
        assert api_key.is_expired() is False

    async def test_validate_api_key_success(self, service):
        """Test validating a correct API key."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key to get a real plain_key and hash
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            user_id=user_id,
            name="Test Key",
        )

        # Mock repository methods for validation
        service.repository.get_by_prefix = AsyncMock(return_value=api_key)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Validate the key
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is not None
        assert validated_key.id == api_key.id
        assert validated_key.account_id == account_id

        # Verify repository methods were called
        service.repository.get_by_prefix.assert_called_once_with(plain_key[:14])
        service.repository.update.assert_called_once()

    async def test_validate_api_key_invalid_key(self, service):
        """Test validating an invalid API key."""
        # Mock repository.get_by_prefix to return None (key not found)
        service.repository.get_by_prefix = AsyncMock(return_value=None)

        # Try to validate a non-existent key
        validated_key = await service.validate_api_key("ldr_invalid_key_12345678901234567890")

        assert validated_key is None
        service.repository.get_by_prefix.assert_called_once()

    async def test_validate_api_key_wrong_hash(self, service):
        """Test validating with wrong key value."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key to get a real api_key entity
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            user_id=user_id,
            name="Test Key",
        )

        # Try to validate with modified key (keep prefix, change rest)
        wrong_key = api_key.key_prefix + "wrong_suffix_12345678901234567890"

        # Mock repository to return the api_key when prefix is looked up
        service.repository.get_by_prefix = AsyncMock(return_value=api_key)

        validated_key = await service.validate_api_key(wrong_key)

        # Should fail because hash doesn't match
        assert validated_key is None

    async def test_validate_revoked_api_key(self, service):
        """Test that revoked keys fail validation."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            user_id=user_id,
            name="Test Key",
        )

        # Revoke the key
        api_key.revoke()

        # Mock repository methods
        service.repository.get_by_prefix = AsyncMock(return_value=api_key)

        # Try to validate
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is None

    async def test_validate_expired_api_key(self, service):
        """Test that expired keys fail validation."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())
        now = datetime.now(UTC)
        past_date = now - timedelta(days=1)

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key with past expiration
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            user_id=user_id,
            name="Expired Key",
            expires_at=past_date,
        )

        # Mock repository methods
        service.repository.get_by_prefix = AsyncMock(return_value=api_key)

        # Try to validate
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is None

    async def test_get_api_key_by_id(self, service):
        """Test retrieving an API key by ID."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key
        api_key, _ = await service.create_api_key(
            account_id=account_id,
            user_id=user_id,
            name="Test Key",
        )

        # Mock repository.get_by_id to return the api_key
        service.repository.get_by_id = AsyncMock(return_value=api_key)

        # Retrieve it
        retrieved = await service.get_api_key(api_key.id)

        assert retrieved is not None
        assert retrieved.id == api_key.id
        assert retrieved.name == "Test Key"

        service.repository.get_by_id.assert_called_once_with(api_key.id)

    async def test_get_api_key_not_found(self, service):
        """Test retrieving a non-existent API key."""
        non_existent_id = APIKeyID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_api_key(non_existent_id)

        assert result is None
        service.repository.get_by_id.assert_called_once_with(non_existent_id)

    async def test_list_account_api_keys(self, service):
        """Test listing all API keys for an account."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return entities as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create multiple API keys
        key1, _ = await service.create_api_key(account_id, user_id, "Production Key")
        key2, _ = await service.create_api_key(account_id, user_id, "Development Key")

        # Mock repository.filter to return both keys
        mock_result = PaginatedResult(
            items=[key1, key2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List them
        keys = await service.list_account_api_keys(account_id)

        assert len(keys) == 2
        names = {key.name for key in keys}
        assert "Production Key" in names
        assert "Development Key" in names

    async def test_list_account_api_keys_active_only(self, service):
        """Test listing only active API keys for an account."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return entities as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API keys
        active_key, _ = await service.create_api_key(account_id, user_id, "Active Key")
        revoked_key, _ = await service.create_api_key(account_id, user_id, "Revoked Key")
        revoked_key.revoke()

        # Mock repository.filter to return only active key when active_only=True
        mock_result = PaginatedResult(
            items=[active_key],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List active only
        active_keys = await service.list_account_api_keys(account_id, active_only=True)

        assert len(active_keys) == 1
        assert active_keys[0].name == "Active Key"

        # Verify filter was called with active_only=True
        service.repository.filter.assert_called_once()
        call_kwargs = service.repository.filter.call_args.kwargs
        assert call_kwargs["active_only"] is True

    async def test_count_active_api_keys(self, service):
        """Test counting active API keys for an account."""
        account_id = AccountID(uuid4())

        # Mock repository.count_active_by_account to return 2
        service.repository.count_active_by_account = AsyncMock(return_value=2)

        # Count active
        count = await service.count_active_api_keys(account_id)

        assert count == 2
        service.repository.count_active_by_account.assert_called_once_with(account_id)

    async def test_revoke_api_key(self, service):
        """Test revoking an API key."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key
        api_key, _ = await service.create_api_key(account_id, user_id, "Test Key")

        assert api_key.status == APIKeyStatus.ACTIVE

        # Mock repository methods for revoke
        service.repository.get_by_id = AsyncMock(return_value=api_key)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Revoke it
        revoked = await service.revoke_api_key(api_key.id)

        assert revoked.status == APIKeyStatus.REVOKED

        # Verify repository methods were called
        service.repository.get_by_id.assert_called_once_with(api_key.id)
        service.repository.update.assert_called_once()

    async def test_record_api_key_usage(self, service):
        """Test recording API key usage."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key
        api_key, _ = await service.create_api_key(account_id, user_id, "Test Key")

        assert api_key.last_used_at is None

        # Mock repository methods for record_usage
        service.repository.get_by_id = AsyncMock(return_value=api_key)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Record usage
        usage_time = datetime.now(UTC)
        updated = await service.record_usage(api_key.id, usage_time)

        assert updated.last_used_at == usage_time

        # Verify repository methods were called
        service.repository.get_by_id.assert_called_once_with(api_key.id)
        service.repository.update.assert_called_once()

    async def test_validate_api_key_records_usage(self, service):
        """Test that validating an API key records its usage."""
        account_id = AccountID(uuid4())
        user_id = UserID(uuid4())

        # Mock repository.create to return the entity as-is
        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Create API key
        api_key, plain_key = await service.create_api_key(account_id, user_id, "Test Key")

        assert api_key.last_used_at is None

        # Mock repository methods for validation
        service.repository.get_by_prefix = AsyncMock(return_value=api_key)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Validate the key (should record usage)
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is not None
        assert validated_key.last_used_at is not None

        # Verify the timestamp is recent (within last 5 seconds)
        time_diff = datetime.now(UTC) - validated_key.last_used_at
        assert time_diff.total_seconds() < 5

        # Verify repository methods were called
        service.repository.get_by_prefix.assert_called_once()
        service.repository.update.assert_called_once()

    async def test_revoke_api_key_not_found(self, service):
        """Test that revoking a non-existent API key raises EntityNotFoundError."""
        non_existent_id = APIKeyID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.revoke_api_key(non_existent_id)

        assert "APIKey not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once_with(non_existent_id)

    async def test_update_api_key_status_not_found(self, service):
        """Test that updating status of non-existent API key raises EntityNotFoundError."""
        non_existent_id = APIKeyID(uuid4())

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.update_api_key_status(non_existent_id, "active")

        assert "APIKey not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once_with(non_existent_id)

    async def test_record_usage_not_found(self, service):
        """Test that recording usage for non-existent API key raises EntityNotFoundError."""
        non_existent_id = APIKeyID(uuid4())
        now = datetime.now(UTC)

        # Mock repository.get_by_id to return None
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.record_usage(non_existent_id, now)

        assert "APIKey not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once_with(non_existent_id)
