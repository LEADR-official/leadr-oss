"""Tests for APIKey domain model."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from leadr.auth.domain.api_key import APIKey, APIKeyStatus


class TestAPIKeyStatus:
    """Test suite for APIKeyStatus enum."""

    def test_status_enum_values(self):
        """Test that APIKeyStatus has correct enum values."""
        assert APIKeyStatus.ACTIVE.value == "active"
        assert APIKeyStatus.REVOKED.value == "revoked"


class TestAPIKey:
    """Test suite for APIKey domain model."""

    def test_create_api_key_with_valid_data(self):
        """Test creating an API key with all required fields."""
        key_id = uuid4()
        account_id = uuid4()
        user_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=90)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=user_id,
            name="Production API Key",
            key_hash="hashed_key_value",
            key_prefix="ldr_abc",
            status=APIKeyStatus.ACTIVE,
            last_used_at=None,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )

        assert api_key.id == key_id
        assert api_key.account_id == account_id
        assert api_key.user_id == user_id
        assert api_key.name == "Production API Key"
        assert api_key.key_hash == "hashed_key_value"
        assert api_key.key_prefix == "ldr_abc"
        assert api_key.status == APIKeyStatus.ACTIVE
        assert api_key.last_used_at is None
        assert api_key.expires_at == expires_at
        assert api_key.created_at == now
        assert api_key.updated_at == now

    def test_create_api_key_defaults_to_active_status(self):
        """Test that API key status defaults to ACTIVE."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_test",
            created_at=now,
            updated_at=now,
        )

        assert api_key.status == APIKeyStatus.ACTIVE

    def test_api_key_name_required(self):
        """Test that API key name is required."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            APIKey(  # type: ignore[call-arg]
                id=key_id,
                account_id=account_id,
                key_hash="hash",
                key_prefix="ldr_test",
                created_at=now,
                updated_at=now,
            )

        assert "name" in str(exc_info.value)

    def test_api_key_account_id_required(self):
        """Test that account_id is required."""
        key_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            APIKey(  # type: ignore[call-arg]
                id=key_id,
                name="Test Key",
                key_hash="hash",
                key_prefix="ldr_test",
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_api_key_user_id_required(self):
        """Test that user_id is required."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            APIKey(  # type: ignore[call-arg]
                id=key_id,
                account_id=account_id,
                name="Test Key",
                key_hash="hash",
                key_prefix="ldr_test",
                created_at=now,
                updated_at=now,
            )

        assert "user_id" in str(exc_info.value)

    def test_api_key_hash_required(self):
        """Test that key_hash is required."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            APIKey(  # type: ignore[call-arg]
                id=key_id,
                account_id=account_id,
                user_id=uuid4(),
                name="Test Key",
                key_prefix="ldr_test",
                created_at=now,
                updated_at=now,
            )

        assert "key_hash" in str(exc_info.value)

    def test_api_key_prefix_required(self):
        """Test that key_prefix is required."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            APIKey(  # type: ignore[call-arg]
                id=key_id,
                account_id=account_id,
                user_id=uuid4(),
                name="Test Key",
                key_hash="hash",
                created_at=now,
                updated_at=now,
            )

        assert "key_prefix" in str(exc_info.value)

    def test_api_key_prefix_must_start_with_ldr(self):
        """Test that key_prefix must start with 'ldr_'."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            APIKey(
                id=key_id,
                account_id=account_id,
                user_id=uuid4(),
                name="Test Key",
                key_hash="hash",
                key_prefix="invalid_prefix",
                created_at=now,
                updated_at=now,
            )

        assert "key_prefix" in str(exc_info.value)
        assert "ldr_" in str(exc_info.value).lower()

    def test_api_key_equality_based_on_id(self):
        """Test that API key equality is based on ID."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key1 = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Key 1",
            key_hash="hash1",
            key_prefix="ldr_abc",
            created_at=now,
            updated_at=now,
        )

        api_key2 = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Key 2",
            key_hash="hash2",
            key_prefix="ldr_xyz",
            created_at=now,
            updated_at=now,
        )

        assert api_key1 == api_key2

    def test_api_key_inequality_different_ids(self):
        """Test that API keys with different IDs are not equal."""
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key1 = APIKey(
            id=uuid4(),
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            created_at=now,
            updated_at=now,
        )

        api_key2 = APIKey(
            id=uuid4(),
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            created_at=now,
            updated_at=now,
        )

        assert api_key1 != api_key2

    def test_api_key_is_hashable(self):
        """Test that API key can be used in sets and as dict keys."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            created_at=now,
            updated_at=now,
        )

        # Should be hashable
        key_set = {api_key}  # type: ignore[var-annotated]
        assert api_key in key_set

        # Should work as dict key
        key_dict = {api_key: "value"}  # type: ignore[dict-item]
        assert key_dict[api_key] == "value"

    def test_revoke_api_key(self):
        """Test revoking an active API key."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            status=APIKeyStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        api_key.revoke()

        assert api_key.status == APIKeyStatus.REVOKED

    def test_is_expired_when_expiration_in_past(self):
        """Test that API key is expired when expires_at is in the past."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)
        past_date = now - timedelta(days=1)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            expires_at=past_date,
            created_at=now,
            updated_at=now,
        )

        assert api_key.is_expired() is True

    def test_is_not_expired_when_expiration_in_future(self):
        """Test that API key is not expired when expires_at is in the future."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)
        future_date = now + timedelta(days=30)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            expires_at=future_date,
            created_at=now,
            updated_at=now,
        )

        assert api_key.is_expired() is False

    def test_is_not_expired_when_no_expiration(self):
        """Test that API key is not expired when expires_at is None."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            expires_at=None,
            created_at=now,
            updated_at=now,
        )

        assert api_key.is_expired() is False

    def test_is_valid_when_active_and_not_expired(self):
        """Test that API key is valid when active and not expired."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)
        future_date = now + timedelta(days=30)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            status=APIKeyStatus.ACTIVE,
            expires_at=future_date,
            created_at=now,
            updated_at=now,
        )

        assert api_key.is_valid() is True

    def test_is_not_valid_when_revoked(self):
        """Test that API key is not valid when revoked."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            status=APIKeyStatus.REVOKED,
            created_at=now,
            updated_at=now,
        )

        assert api_key.is_valid() is False

    def test_is_not_valid_when_expired(self):
        """Test that API key is not valid when expired."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)
        past_date = now - timedelta(days=1)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            status=APIKeyStatus.ACTIVE,
            expires_at=past_date,
            created_at=now,
            updated_at=now,
        )

        assert api_key.is_valid() is False

    def test_record_usage_updates_last_used_at(self):
        """Test that record_usage updates last_used_at timestamp."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            last_used_at=None,
            created_at=now,
            updated_at=now,
        )

        assert api_key.last_used_at is None

        usage_time = datetime.now(UTC)
        api_key.record_usage(usage_time)

        assert api_key.last_used_at == usage_time

    def test_api_key_immutability_of_id(self):
        """Test that API key ID cannot be changed after creation."""
        key_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            created_at=now,
            updated_at=now,
        )

        new_id = uuid4()

        with pytest.raises(ValidationError):
            api_key.id = new_id

    def test_account_id_as_uuid(self):
        """Test that account_id can be created from UUID."""
        key_id = uuid4()
        account_id = UUID("12345678-1234-5678-1234-567812345678")
        now = datetime.now(UTC)

        api_key = APIKey(
            id=key_id,
            account_id=account_id,
            user_id=uuid4(),
            name="Test Key",
            key_hash="hash",
            key_prefix="ldr_abc",
            created_at=now,
            updated_at=now,
        )

        assert api_key.account_id == account_id
