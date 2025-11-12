"""Tests for Device domain model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.auth.domain.device import Device, DeviceSession, DeviceStatus


class TestDeviceStatus:
    """Test suite for DeviceStatus enum."""

    def test_status_enum_values(self):
        """Test that DeviceStatus has correct enum values."""
        assert DeviceStatus.ACTIVE.value == "active"
        assert DeviceStatus.BANNED.value == "banned"
        assert DeviceStatus.SUSPENDED.value == "suspended"


class TestDevice:
    """Test suite for Device domain model."""

    def test_create_device_with_valid_data(self):
        """Test creating a device with all required fields."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            metadata={"platform": "ios", "version": "1.0.0"},
            created_at=now,
            updated_at=now,
        )

        assert device.id == device_id_value
        assert device.game_id == game_id
        assert device.device_id == "test-device-123"
        assert device.account_id == account_id
        assert device.status == DeviceStatus.ACTIVE
        assert device.first_seen_at == now
        assert device.last_seen_at == now
        assert device.metadata == {"platform": "ios", "version": "1.0.0"}

    def test_create_device_defaults_to_active_status(self):
        """Test that device status defaults to ACTIVE."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device.status == DeviceStatus.ACTIVE

    def test_create_device_with_empty_metadata(self):
        """Test that device can be created with empty metadata."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            metadata={},
            created_at=now,
            updated_at=now,
        )

        assert device.metadata == {}

    def test_device_id_required(self):
        """Test that device_id is required."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Device(  # type: ignore[call-arg]
                id=device_id_value,
                game_id=game_id,
                account_id=account_id,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "device_id" in str(exc_info.value)

    def test_game_id_required(self):
        """Test that game_id is required."""
        device_id_value = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Device(  # type: ignore[call-arg]
                id=device_id_value,
                device_id="test-device-123",
                account_id=account_id,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "game_id" in str(exc_info.value)

    def test_account_id_required(self):
        """Test that account_id is required."""
        device_id_value = uuid4()
        game_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Device(  # type: ignore[call-arg]
                id=device_id_value,
                game_id=game_id,
                device_id="test-device-123",
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_is_active_when_status_active(self):
        """Test that is_active returns True when status is ACTIVE."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device.is_active() is True

    def test_is_not_active_when_status_banned(self):
        """Test that is_active returns False when status is BANNED."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            status=DeviceStatus.BANNED,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device.is_active() is False

    def test_is_not_active_when_status_suspended(self):
        """Test that is_active returns False when status is SUSPENDED."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            status=DeviceStatus.SUSPENDED,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device.is_active() is False

    def test_ban_device(self):
        """Test banning an active device."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        device.ban()

        assert device.status == DeviceStatus.BANNED

    def test_suspend_device(self):
        """Test suspending an active device."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            status=DeviceStatus.ACTIVE,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        device.suspend()

        assert device.status == DeviceStatus.SUSPENDED

    def test_activate_device(self):
        """Test activating a banned device."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            status=DeviceStatus.BANNED,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        device.activate()

        assert device.status == DeviceStatus.ACTIVE

    def test_update_last_seen(self):
        """Test updating last_seen_at timestamp."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)
        earlier = now - timedelta(hours=1)

        device = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            first_seen_at=earlier,
            last_seen_at=earlier,
            created_at=now,
            updated_at=now,
        )

        assert device.last_seen_at == earlier

        device.update_last_seen()

        # Should be updated to current time (within 1 second tolerance)
        assert device.last_seen_at > earlier
        assert (datetime.now(UTC) - device.last_seen_at).total_seconds() < 1

    def test_device_equality_based_on_id(self):
        """Test that device equality is based on ID."""
        device_id_value = uuid4()
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device1 = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="device-1",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        device2 = Device(
            id=device_id_value,
            game_id=game_id,
            device_id="device-2",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device1 == device2

    def test_device_inequality_different_ids(self):
        """Test that devices with different IDs are not equal."""
        game_id = uuid4()
        account_id = uuid4()
        now = datetime.now(UTC)

        device1 = Device(
            id=uuid4(),
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        device2 = Device(
            id=uuid4(),
            game_id=game_id,
            device_id="test-device-123",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device1 != device2


class TestDeviceSession:
    """Test suite for DeviceSession domain model."""

    def test_create_device_session_with_valid_data(self):
        """Test creating a device session with all required fields."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)
        refresh_expires_at = now + timedelta(days=30)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            refresh_token_hash="refresh_hash",
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.id == session_id
        assert session.device_id == device_id
        assert session.access_token_hash == "hashed_token_value"
        assert session.expires_at == expires_at
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0"
        assert session.revoked_at is None

    def test_create_device_session_with_optional_fields_none(self):
        """Test that device session can be created with optional fields as None."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=expires_at,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            ip_address=None,
            user_agent=None,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.ip_address is None
        assert session.user_agent is None
        assert session.revoked_at is None

    def test_device_id_required(self):
        """Test that device_id is required."""
        session_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            DeviceSession(  # type: ignore[call-arg]
                id=session_id,
                access_token_hash="hashed_token_value",
                expires_at=expires_at,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
                created_at=now,
                updated_at=now,
            )

        assert "device_id" in str(exc_info.value)

    def test_access_token_hash_required(self):
        """Test that access_token_hash is required."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            DeviceSession(  # type: ignore[call-arg]
                id=session_id,
                device_id=device_id,
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "access_token_hash" in str(exc_info.value)

    def test_expires_at_required(self):
        """Test that expires_at is required."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            DeviceSession(  # type: ignore[call-arg]
                id=session_id,
                device_id=device_id,
                access_token_hash="hashed_token_value",
                created_at=now,
                updated_at=now,
            )

        assert "expires_at" in str(exc_info.value)

    def test_is_expired_when_expiration_in_past(self):
        """Test that session is expired when expires_at is in the past."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        past_date = now - timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=past_date,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )

        assert session.is_expired() is True

    def test_is_not_expired_when_expiration_in_future(self):
        """Test that session is not expired when expires_at is in the future."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=future_date,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )

        assert session.is_expired() is False

    def test_is_revoked_when_revoked_at_set(self):
        """Test that session is revoked when revoked_at is set."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=expires_at,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=now,
            created_at=now,
            updated_at=now,
        )

        assert session.is_revoked() is True

    def test_is_not_revoked_when_revoked_at_none(self):
        """Test that session is not revoked when revoked_at is None."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=expires_at,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.is_revoked() is False

    def test_is_valid_when_not_expired_and_not_revoked(self):
        """Test that session is valid when not expired and not revoked."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=future_date,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.is_valid() is True

    def test_is_not_valid_when_expired(self):
        """Test that session is not valid when expired."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        past_date = now - timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=past_date,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.is_valid() is False

    def test_is_not_valid_when_revoked(self):
        """Test that session is not valid when revoked."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=future_date,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=now,
            created_at=now,
            updated_at=now,
        )

        assert session.is_valid() is False

    def test_revoke_session(self):
        """Test revoking an active session."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        future_date = now + timedelta(hours=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hashed_token_value",
            expires_at=future_date,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        assert session.revoked_at is None

        session.revoke()

        assert session.revoked_at is not None
        # Should be set to current time (within 1 second tolerance)
        assert (datetime.now(UTC) - session.revoked_at).total_seconds() < 1

    def test_session_equality_based_on_id(self):
        """Test that session equality is based on ID."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=1)

        session1 = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hash1",
            expires_at=expires_at,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )

        session2 = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="hash2",
            expires_at=expires_at,
            refresh_token_hash="refresh_hash",
            refresh_expires_at=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )

        assert session1 == session2

    def test_create_device_session_with_refresh_token_fields(self):
        """Test creating a device session with refresh token fields."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)
        refresh_expires_at = now + timedelta(days=30)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session.refresh_token_hash == "refresh_hash"
        assert session.token_version == 1
        assert session.refresh_expires_at == refresh_expires_at

    def test_token_version_defaults_to_one(self):
        """Test that token_version defaults to 1."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)
        refresh_expires_at = now + timedelta(days=30)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session.token_version == 1

    def test_refresh_token_hash_required(self):
        """Test that refresh_token_hash is required."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)
        refresh_expires_at = now + timedelta(days=30)

        with pytest.raises(ValidationError) as exc_info:
            DeviceSession(  # type: ignore[call-arg]
                id=session_id,
                device_id=device_id,
                access_token_hash="access_hash",
                expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "refresh_token_hash" in str(exc_info.value)

    def test_refresh_expires_at_required(self):
        """Test that refresh_expires_at is required."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)

        with pytest.raises(ValidationError) as exc_info:
            DeviceSession(  # type: ignore[call-arg]
                id=session_id,
                device_id=device_id,
                access_token_hash="access_hash",
                refresh_token_hash="refresh_hash",
                expires_at=access_expires_at,
                created_at=now,
                updated_at=now,
            )

        assert "refresh_expires_at" in str(exc_info.value)

    def test_is_refresh_expired_when_refresh_expiration_in_past(self):
        """Test that session refresh token is expired when refresh_expires_at is in the past."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)
        past_date = now - timedelta(days=1)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            expires_at=access_expires_at,
            refresh_expires_at=past_date,
            created_at=now,
            updated_at=now,
        )

        assert session.is_refresh_expired() is True

    def test_is_refresh_not_expired_when_refresh_expiration_in_future(self):
        """Test that session refresh token is not expired when refresh_expires_at is in the future."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)
        future_date = now + timedelta(days=30)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            expires_at=access_expires_at,
            refresh_expires_at=future_date,
            created_at=now,
            updated_at=now,
        )

        assert session.is_refresh_expired() is False

    def test_rotate_tokens_increments_version(self):
        """Test that rotate_tokens increments token_version."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)
        refresh_expires_at = now + timedelta(days=30)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        assert session.token_version == 1

        session.rotate_tokens()

        assert session.token_version == 2

    def test_rotate_tokens_multiple_times(self):
        """Test that rotate_tokens can be called multiple times."""
        session_id = uuid4()
        device_id = uuid4()
        now = datetime.now(UTC)
        access_expires_at = now + timedelta(minutes=15)
        refresh_expires_at = now + timedelta(days=30)

        session = DeviceSession(
            id=session_id,
            device_id=device_id,
            access_token_hash="access_hash",
            refresh_token_hash="refresh_hash",
            token_version=1,
            expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            created_at=now,
            updated_at=now,
        )

        session.rotate_tokens()
        session.rotate_tokens()
        session.rotate_tokens()

        assert session.token_version == 4
