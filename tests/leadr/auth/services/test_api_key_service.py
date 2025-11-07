"""Tests for APIKey service."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.services.api_key_service import APIKeyService
from leadr.auth.services.repositories import APIKeyRepository
from leadr.common.domain.models import EntityID


@pytest.mark.asyncio
class TestAPIKeyService:
    """Test suite for APIKey service."""

    async def test_create_api_key(self, db_session: AsyncSession):
        """Test creating an API key with automatic generation and hashing."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API key via service
        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Production Key",
            expires_at=None,
        )

        # Verify key was created
        assert api_key.account_id == account_id
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

    async def test_create_api_key_with_expiration(self, db_session: AsyncSession):
        """Test creating an API key with an expiration date."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API key with expiration
        service = APIKeyService(db_session)
        expires_at = now + timedelta(days=90)

        api_key, _ = await service.create_api_key(
            account_id=account_id,
            name="Temporary Key",
            expires_at=expires_at,
        )

        assert api_key.expires_at == expires_at
        assert api_key.is_expired() is False

    async def test_validate_api_key_success(self, db_session: AsyncSession):
        """Test validating a correct API key."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API key
        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Test Key",
        )

        # Validate the key
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is not None
        assert validated_key.id == api_key.id
        assert validated_key.account_id == account_id

    async def test_validate_api_key_invalid_key(self, db_session: AsyncSession):
        """Test validating an invalid API key."""
        service = APIKeyService(db_session)

        # Try to validate a non-existent key
        validated_key = await service.validate_api_key("ldr_invalid_key_12345678901234567890")

        assert validated_key is None

    async def test_validate_api_key_wrong_hash(self, db_session: AsyncSession):
        """Test validating with wrong key value."""
        # Create account and API key
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Test Key",
        )

        # Try to validate with modified key (keep prefix, change rest)
        wrong_key = api_key.key_prefix + "wrong_suffix_12345678901234567890"
        validated_key = await service.validate_api_key(wrong_key)

        assert validated_key is None

    async def test_validate_revoked_api_key(self, db_session: AsyncSession):
        """Test that revoked keys fail validation."""
        # Create account and API key
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Test Key",
        )

        # Revoke the key
        await service.revoke_api_key(api_key.id)

        # Try to validate
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is None

    async def test_validate_expired_api_key(self, db_session: AsyncSession):
        """Test that expired keys fail validation."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API key with past expiration
        service = APIKeyService(db_session)
        past_date = now - timedelta(days=1)

        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name="Expired Key",
            expires_at=past_date,
        )

        # Try to validate
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is None

    async def test_get_api_key_by_id(self, db_session: AsyncSession):
        """Test retrieving an API key by ID."""
        # Create account and API key
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        service = APIKeyService(db_session)
        api_key, _ = await service.create_api_key(
            account_id=account_id,
            name="Test Key",
        )

        # Retrieve it
        retrieved = await service.get_api_key(api_key.id)

        assert retrieved is not None
        assert retrieved.id == api_key.id
        assert retrieved.name == "Test Key"

    async def test_get_api_key_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent API key."""
        service = APIKeyService(db_session)
        non_existent_id = EntityID.generate()

        result = await service.get_api_key(non_existent_id)

        assert result is None

    async def test_list_account_api_keys(self, db_session: AsyncSession):
        """Test listing all API keys for an account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create multiple API keys
        service = APIKeyService(db_session)
        await service.create_api_key(account_id, "Production Key")
        await service.create_api_key(account_id, "Development Key")

        # List them
        keys = await service.list_account_api_keys(account_id)

        assert len(keys) == 2
        names = {key.name for key in keys}
        assert "Production Key" in names
        assert "Development Key" in names

    async def test_list_account_api_keys_active_only(self, db_session: AsyncSession):
        """Test listing only active API keys for an account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API keys
        service = APIKeyService(db_session)
        active_key, _ = await service.create_api_key(account_id, "Active Key")
        revoked_key, _ = await service.create_api_key(account_id, "Revoked Key")

        # Revoke one
        await service.revoke_api_key(revoked_key.id)

        # List active only
        active_keys = await service.list_account_api_keys(account_id, active_only=True)

        assert len(active_keys) == 1
        assert active_keys[0].name == "Active Key"

    async def test_count_active_api_keys(self, db_session: AsyncSession):
        """Test counting active API keys for an account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create API keys
        service = APIKeyService(db_session)
        await service.create_api_key(account_id, "Key 1")
        await service.create_api_key(account_id, "Key 2")
        key3, _ = await service.create_api_key(account_id, "Key 3")

        # Revoke one
        await service.revoke_api_key(key3.id)

        # Count active
        count = await service.count_active_api_keys(account_id)

        assert count == 2

    async def test_revoke_api_key(self, db_session: AsyncSession):
        """Test revoking an API key."""
        # Create account and API key
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        service = APIKeyService(db_session)
        api_key, _ = await service.create_api_key(account_id, "Test Key")

        assert api_key.status == APIKeyStatus.ACTIVE

        # Revoke it
        revoked = await service.revoke_api_key(api_key.id)

        assert revoked.status == APIKeyStatus.REVOKED

        # Verify in database
        retrieved = await service.get_api_key(api_key.id)
        assert retrieved is not None
        assert retrieved.status == APIKeyStatus.REVOKED

    async def test_record_api_key_usage(self, db_session: AsyncSession):
        """Test recording API key usage."""
        # Create account and API key
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        service = APIKeyService(db_session)
        api_key, _ = await service.create_api_key(account_id, "Test Key")

        assert api_key.last_used_at is None

        # Record usage
        usage_time = datetime.now(UTC)
        updated = await service.record_usage(api_key.id, usage_time)

        assert updated.last_used_at == usage_time

        # Verify in database
        retrieved = await service.get_api_key(api_key.id)
        assert retrieved is not None
        assert retrieved.last_used_at == usage_time

    async def test_validate_api_key_records_usage(self, db_session: AsyncSession):
        """Test that validating an API key records its usage."""
        # Create account and API key
        account_repo = AccountRepository(db_session)
        account_id = EntityID.generate()
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        service = APIKeyService(db_session)
        api_key, plain_key = await service.create_api_key(account_id, "Test Key")

        assert api_key.last_used_at is None

        # Validate the key (should record usage)
        validated_key = await service.validate_api_key(plain_key)

        assert validated_key is not None
        assert validated_key.last_used_at is not None

        # Verify the timestamp is recent (within last 5 seconds)
        time_diff = datetime.now(UTC) - validated_key.last_used_at
        assert time_diff.total_seconds() < 5
