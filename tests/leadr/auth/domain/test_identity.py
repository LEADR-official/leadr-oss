"""Tests for Identity domain model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.auth.domain.identity import Identity, IdentityKind, IdentitySession
from leadr.common.domain.ids import AccountID, GameID, IdentityID, IdentitySessionID


class TestIdentityKind:
    """Test suite for IdentityKind enum."""

    def test_kind_enum_values(self):
        """Test that IdentityKind has correct enum values."""
        assert IdentityKind.DEVICE.value == "DEVICE"
        assert IdentityKind.STEAM.value == "STEAM"
        assert IdentityKind.CUSTOM.value == "CUSTOM"


class TestIdentity:
    """Test suite for Identity domain model."""

    def test_create_identity_with_valid_data(self):
        """Test creating an identity with all required fields."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345678-1234-1234-1234-123456789012",
            display_name="Test Player",
            created_at=now,
            updated_at=now,
        )

        assert identity.id == identity_id
        assert identity.account_id == account_id
        assert identity.game_id == game_id
        assert identity.kind == IdentityKind.DEVICE
        assert identity.external_key == "dev_12345678-1234-1234-1234-123456789012"
        assert identity.display_name == "Test Player"

    def test_create_identity_without_display_name(self):
        """Test that identity can be created without display_name."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.STEAM,
            external_key="76561198012345678",
            created_at=now,
            updated_at=now,
        )

        assert identity.display_name is None

    def test_create_identity_with_custom_kind(self):
        """Test creating an identity with CUSTOM kind."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.CUSTOM,
            external_key="custom_user_123",
            display_name="CustomPlayer",
            created_at=now,
            updated_at=now,
        )

        assert identity.kind == IdentityKind.CUSTOM

    def test_account_id_required(self):
        """Test that account_id is required."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Identity(  # type: ignore[call-arg]
                id=identity_id,
                game_id=game_id,
                kind=IdentityKind.DEVICE,
                external_key="dev_12345",
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_game_id_required(self):
        """Test that game_id is required."""
        identity_id = IdentityID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Identity(  # type: ignore[call-arg]
                id=identity_id,
                account_id=account_id,
                kind=IdentityKind.DEVICE,
                external_key="dev_12345",
                created_at=now,
                updated_at=now,
            )

        assert "game_id" in str(exc_info.value)

    def test_external_key_required(self):
        """Test that external_key is required."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Identity(  # type: ignore[call-arg]
                id=identity_id,
                account_id=account_id,
                game_id=game_id,
                kind=IdentityKind.DEVICE,
                created_at=now,
                updated_at=now,
            )

        assert "external_key" in str(exc_info.value)

    def test_kind_required(self):
        """Test that kind is required."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Identity(  # type: ignore[call-arg]
                id=identity_id,
                account_id=account_id,
                game_id=game_id,
                external_key="dev_12345",
                created_at=now,
                updated_at=now,
            )

        assert "kind" in str(exc_info.value)

    def test_update_display_name(self):
        """Test updating display name."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345",
            display_name="Original Name",
            created_at=now,
            updated_at=now,
        )

        identity.update_display_name("New Name")

        assert identity.display_name == "New Name"

    def test_update_display_name_to_none(self):
        """Test updating display name to None."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        identity = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345",
            display_name="Original Name",
            created_at=now,
            updated_at=now,
        )

        identity.update_display_name(None)

        assert identity.display_name is None

    def test_identity_equality_based_on_id(self):
        """Test that identity equality is based on ID."""
        identity_id = IdentityID(uuid4())
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        identity1 = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345",
            display_name="Name 1",
            created_at=now,
            updated_at=now,
        )

        identity2 = Identity(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345",
            display_name="Name 2",
            created_at=now,
            updated_at=now,
        )

        assert identity1 == identity2

    def test_identity_inequality_different_ids(self):
        """Test that identities with different IDs are not equal."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        identity1 = Identity(
            id=IdentityID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345",
            created_at=now,
            updated_at=now,
        )

        identity2 = Identity(
            id=IdentityID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key="dev_12345",
            created_at=now,
            updated_at=now,
        )

        assert identity1 != identity2


class TestIdentitySession:
    """Test suite for IdentitySession domain model."""

    def test_create_identity_session_with_valid_data(self):
        """Test creating an identity session with all required fields."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            token_version=1,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.id == session_id
        assert session.identity_id == identity_id
        assert session.access_token_hash == "hashed_access_token"
        assert session.refresh_token_hash == "hashed_refresh_token"
        assert session.token_version == 1
        assert session.expires_at == expires_at
        assert session.refresh_expires_at == refresh_expires_at
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0"
        assert session.revoked_at is None

    def test_create_identity_session_with_optional_fields_none(self):
        """Test that identity session can be created with optional fields as None."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            ip_address=None,
            user_agent=None,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.ip_address is None
        assert session.user_agent is None
        assert session.revoked_at is None

    def test_identity_id_required(self):
        """Test that identity_id is required."""
        session_id = IdentitySessionID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        with pytest.raises(ValidationError) as exc_info:
            IdentitySession(  # type: ignore[call-arg]
                id=session_id,
                access_token_hash="hashed_access_token",
                refresh_token_hash="hashed_refresh_token",
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "identity_id" in str(exc_info.value)

    def test_access_token_hash_required(self):
        """Test that access_token_hash is required."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        with pytest.raises(ValidationError) as exc_info:
            IdentitySession(  # type: ignore[call-arg]
                id=session_id,
                identity_id=identity_id,
                refresh_token_hash="hashed_refresh_token",
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "access_token_hash" in str(exc_info.value)

    def test_refresh_token_hash_required(self):
        """Test that refresh_token_hash is required."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        with pytest.raises(ValidationError) as exc_info:
            IdentitySession(  # type: ignore[call-arg]
                id=session_id,
                identity_id=identity_id,
                access_token_hash="hashed_access_token",
                expires_at=expires_at,
                refresh_expires_at=refresh_expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "refresh_token_hash" in str(exc_info.value)

    def test_expires_at_required(self):
        """Test that expires_at is required."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        refresh_expires_at = now + timedelta(days=30)

        with pytest.raises(ValidationError) as exc_info:
            IdentitySession(  # type: ignore[call-arg]
                id=session_id,
                identity_id=identity_id,
                access_token_hash="hashed_access_token",
                refresh_token_hash="hashed_refresh_token",
                refresh_expires_at=refresh_expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "expires_at" in str(exc_info.value)

    def test_refresh_expires_at_required(self):
        """Test that refresh_expires_at is required."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            IdentitySession(  # type: ignore[call-arg]
                id=session_id,
                identity_id=identity_id,
                access_token_hash="hashed_access_token",
                refresh_token_hash="hashed_refresh_token",
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "refresh_expires_at" in str(exc_info.value)

    def test_token_version_defaults_to_one(self):
        """Test that token_version defaults to 1."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session.token_version == 1

    def test_is_expired_when_expiration_in_past(self):
        """Test that session is expired when expires_at is in the past."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        past_date = now - timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=past_date,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session.is_expired() is True

    def test_is_not_expired_when_expiration_in_future(self):
        """Test that session is not expired when expires_at is in the future."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=future_date,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session.is_expired() is False

    def test_is_refresh_expired_when_refresh_expiration_in_past(self):
        """Test that refresh token is expired when refresh_expires_at is in the past."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        past_date = now - timedelta(days=1)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=expires_at,
            refresh_expires_at=past_date,
            created_at=now,
            updated_at=now,
        )

        assert session.is_refresh_expired() is True

    def test_is_refresh_not_expired_when_refresh_expiration_in_future(self):
        """Test that refresh token is not expired when refresh_expires_at is in future."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        future_date = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=expires_at,
            refresh_expires_at=future_date,
            created_at=now,
            updated_at=now,
        )

        assert session.is_refresh_expired() is False

    def test_is_revoked_when_revoked_at_set(self):
        """Test that session is revoked when revoked_at is set."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            revoked_at=now,
            created_at=now,
            updated_at=now,
        )

        assert session.is_revoked() is True

    def test_is_not_revoked_when_revoked_at_none(self):
        """Test that session is not revoked when revoked_at is None."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.is_revoked() is False

    def test_is_valid_when_not_expired_and_not_revoked(self):
        """Test that session is valid when not expired and not revoked."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=future_date,
            refresh_expires_at=refresh_expires_at,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.is_valid() is True

    def test_is_not_valid_when_expired(self):
        """Test that session is not valid when expired."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        past_date = now - timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=past_date,
            refresh_expires_at=refresh_expires_at,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.is_valid() is False

    def test_is_not_valid_when_revoked(self):
        """Test that session is not valid when revoked."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=future_date,
            refresh_expires_at=refresh_expires_at,
            revoked_at=now,
            created_at=now,
            updated_at=now,
        )

        assert session.is_valid() is False

    def test_revoke_session(self):
        """Test revoking an active session."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            expires_at=future_date,
            refresh_expires_at=refresh_expires_at,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.revoked_at is None

        session.revoke()

        assert session.revoked_at is not None
        # Should be set to current time (within 1 second tolerance)
        assert (datetime.now(UTC) - session.revoked_at).total_seconds() < 1

    def test_rotate_tokens_increments_version(self):
        """Test that rotate_tokens increments token_version."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            token_version=1,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session.token_version == 1

        session.rotate_tokens()

        assert session.token_version == 2

    def test_rotate_tokens_multiple_times(self):
        """Test that rotate_tokens can be called multiple times."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hashed_access_token",
            refresh_token_hash="hashed_refresh_token",
            token_version=1,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        session.rotate_tokens()
        session.rotate_tokens()
        session.rotate_tokens()

        assert session.token_version == 4

    def test_session_equality_based_on_id(self):
        """Test that session equality is based on ID."""
        session_id = IdentitySessionID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session1 = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hash1",
            refresh_token_hash="refresh_hash1",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        session2 = IdentitySession(
            id=session_id,
            identity_id=identity_id,
            access_token_hash="hash2",
            refresh_token_hash="refresh_hash2",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session1 == session2
