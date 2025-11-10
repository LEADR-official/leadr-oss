"""Tests for APIKey repository service."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.services.repositories import APIKeyRepository
from leadr.common.domain.models import EntityID


@pytest.mark.asyncio
class TestAPIKeyRepository:
    """Test suite for APIKey repository."""

    async def test_create_api_key(self, db_session: AsyncSession):
        """Test creating an API key via repository."""
        # Create account first
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
        api_key_repo = APIKeyRepository(db_session)
        key_id = EntityID.generate()

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            name="Production API Key",
            key_hash="hashed_key_value",
            key_prefix="ldr_abc123",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        created = await api_key_repo.create(api_key)

        assert created.id == key_id
        assert created.account_id == account_id
        assert created.name == "Production API Key"
        assert created.key_hash == "hashed_key_value"
        assert created.key_prefix == "ldr_abc123"
        assert created.status == APIKeyStatus.ACTIVE

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

        api_key_repo = APIKeyRepository(db_session)
        key_id = EntityID.generate()

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_test",
            created_at=now,
            updated_at=now,
        )
        await api_key_repo.create(api_key)

        # Retrieve it
        retrieved = await api_key_repo.get_by_id(key_id)

        assert retrieved is not None
        assert retrieved.id == key_id
        assert retrieved.name == "Test Key"

    async def test_get_api_key_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent API key returns None."""
        api_key_repo = APIKeyRepository(db_session)
        non_existent_id = EntityID.generate()

        result = await api_key_repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_api_key_by_prefix(self, db_session: AsyncSession):
        """Test retrieving an API key by its prefix."""
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

        api_key_repo = APIKeyRepository(db_session)
        key_id = EntityID.generate()

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_unique123",
            created_at=now,
            updated_at=now,
        )
        await api_key_repo.create(api_key)

        # Retrieve by prefix
        retrieved = await api_key_repo.get_by_prefix("ldr_unique123")

        assert retrieved is not None
        assert retrieved.id == key_id
        assert retrieved.key_prefix == "ldr_unique123"

    async def test_get_api_key_by_prefix_not_found(self, db_session: AsyncSession):
        """Test retrieving by non-existent prefix returns None."""
        api_key_repo = APIKeyRepository(db_session)

        result = await api_key_repo.get_by_prefix("ldr_nonexistent")

        assert result is None

    async def test_list_api_keys_by_account(self, db_session: AsyncSession):
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
        api_key_repo = APIKeyRepository(db_session)

        key1 = APIKey(
            id=EntityID.generate(),
            account_id=account_id,
            name="Production Key",
            key_hash="hash1",
            key_prefix="ldr_prod",
            created_at=now,
            updated_at=now,
        )
        key2 = APIKey(
            id=EntityID.generate(),
            account_id=account_id,
            name="Development Key",
            key_hash="hash2",
            key_prefix="ldr_dev",
            created_at=now,
            updated_at=now,
        )

        await api_key_repo.create(key1)
        await api_key_repo.create(key2)

        # List keys for account
        keys = await api_key_repo.filter(account_id)

        assert len(keys) == 2
        names = {key.name for key in keys}
        assert "Production Key" in names
        assert "Development Key" in names

    async def test_list_active_api_keys_by_account(self, db_session: AsyncSession):
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

        # Create API keys with different statuses
        api_key_repo = APIKeyRepository(db_session)

        active_key = APIKey(
            id=EntityID.generate(),
            account_id=account_id,
            name="Active Key",
            key_hash="hash1",
            key_prefix="ldr_active",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        revoked_key = APIKey(
            id=EntityID.generate(),
            account_id=account_id,
            name="Revoked Key",
            key_hash="hash2",
            key_prefix="ldr_revoked",
            status=APIKeyStatus.REVOKED,
            created_at=now,
            updated_at=now,
        )

        await api_key_repo.create(active_key)
        await api_key_repo.create(revoked_key)

        # List only active keys
        active_keys = await api_key_repo.filter(account_id, active_only=True)

        assert len(active_keys) == 1
        assert active_keys[0].name == "Active Key"
        assert active_keys[0].status == APIKeyStatus.ACTIVE

    async def test_count_active_api_keys_by_account(self, db_session: AsyncSession):
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
        api_key_repo = APIKeyRepository(db_session)

        for i in range(3):
            key = APIKey(
                id=EntityID.generate(),
                account_id=account_id,
                name=f"Key {i}",
                key_hash=f"hash{i}",
                key_prefix=f"ldr_key{i}",
                status=APIKeyStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            await api_key_repo.create(key)

        # Create one revoked key
        revoked_key = APIKey(
            id=EntityID.generate(),
            account_id=account_id,
            name="Revoked Key",
            key_hash="revoked_hash",
            key_prefix="ldr_revoked",
            status=APIKeyStatus.REVOKED,
            created_at=now,
            updated_at=now,
        )
        await api_key_repo.create(revoked_key)

        # Count active keys
        count = await api_key_repo.count_active_by_account(account_id)

        assert count == 3

    async def test_update_api_key(self, db_session: AsyncSession):
        """Test updating an API key via repository."""
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

        api_key_repo = APIKeyRepository(db_session)
        key_id = EntityID.generate()

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            last_used_at=None,
            created_at=now,
            updated_at=now,
        )
        await api_key_repo.create(api_key)

        # Update it
        usage_time = datetime.now(UTC)
        api_key.record_usage(usage_time)
        updated = await api_key_repo.update(api_key)

        assert updated.last_used_at == usage_time

        # Verify in database
        retrieved = await api_key_repo.get_by_id(key_id)
        assert retrieved is not None
        assert retrieved.last_used_at == usage_time

    async def test_update_api_key_status(self, db_session: AsyncSession):
        """Test updating an API key status."""
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

        api_key_repo = APIKeyRepository(db_session)
        key_id = EntityID.generate()

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_test",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await api_key_repo.create(api_key)

        # Revoke it
        api_key.revoke()
        updated = await api_key_repo.update(api_key)

        assert updated.status == APIKeyStatus.REVOKED

        # Verify in database
        retrieved = await api_key_repo.get_by_id(key_id)
        assert retrieved is not None
        assert retrieved.status == APIKeyStatus.REVOKED

    async def test_delete_api_key(self, db_session: AsyncSession):
        """Test deleting an API key via repository."""
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

        api_key_repo = APIKeyRepository(db_session)
        key_id = EntityID.generate()

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_test",
            created_at=now,
            updated_at=now,
        )
        await api_key_repo.create(api_key)

        # Delete it
        await api_key_repo.delete(key_id)

        # Verify it's gone
        retrieved = await api_key_repo.get_by_id(key_id)
        assert retrieved is None

    async def test_api_key_with_expiration(self, db_session: AsyncSession):
        """Test creating and retrieving an API key with expiration."""
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
        api_key_repo = APIKeyRepository(db_session)
        key_id = EntityID.generate()
        expires_at = now + timedelta(days=90)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            name="Temporary Key",
            key_hash="hash",
            key_prefix="ldr_temp",
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        await api_key_repo.create(api_key)

        # Retrieve and verify expiration
        retrieved = await api_key_repo.get_by_id(key_id)

        assert retrieved is not None
        assert retrieved.expires_at == expires_at
        assert retrieved.is_expired() is False
