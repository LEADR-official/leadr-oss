"""Tests for Device domain model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.auth.domain.device import Device, DeviceStatus
from leadr.common.domain.ids import AccountID, DeviceID, GameID


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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        assert (
            device.client_fingerprint
            == "cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0"
        )
        assert device.account_id == account_id
        assert device.status == DeviceStatus.ACTIVE
        assert device.first_seen_at == now
        assert device.last_seen_at == now
        assert device.metadata == {"platform": "ios", "version": "1.0.0"}

    def test_create_device_defaults_to_active_status(self):
        """Test that device status defaults to ACTIVE."""
        device_id_value = uuid4()
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            metadata={},
            created_at=now,
            updated_at=now,
        )

        assert device.metadata == {}

    def test_client_fingerprint_required(self):
        """Test that client_fingerprint is required."""
        device_id_value = uuid4()
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Device(  # type: ignore[call-arg]
                id=DeviceID(device_id_value),
                game_id=game_id,
                account_id=account_id,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "client_fingerprint" in str(exc_info.value)

    def test_game_id_required(self):
        """Test that game_id is required."""
        device_id_value = uuid4()
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Device(  # type: ignore[call-arg]
                id=DeviceID(device_id_value),
                client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Device(  # type: ignore[call-arg]
                id=DeviceID(device_id_value),
                game_id=game_id,
                client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "account_id" in str(exc_info.value)

    def test_is_active_when_status_active(self):
        """Test that is_active returns True when status is ACTIVE."""
        device_id_value = uuid4()
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        earlier = now - timedelta(hours=1)

        device = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device1 = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="03204de92e11fc8c528139be419065920eb83dbff1a4663bbea455aa6e9702bd",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        device2 = Device(
            id=DeviceID(device_id_value),
            game_id=game_id,
            client_fingerprint="588605bf5362e8b7f170c8b2926c4061ab09a7d95c74c6ff9b45140b6787e0de",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device1 == device2

    def test_device_inequality_different_ids(self):
        """Test that devices with different IDs are not equal."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        device1 = Device(
            id=DeviceID(uuid4()),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        device2 = Device(
            id=DeviceID(uuid4()),
            game_id=game_id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device1 != device2

    def test_client_fingerprint_accepts_valid_sha256(self):
        """Test that client_fingerprint accepts valid SHA256 hash."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        valid_sha256 = "a" * 64  # 64 lowercase hex characters

        device = Device(
            id=DeviceID(uuid4()),
            game_id=game_id,
            client_fingerprint=valid_sha256,
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        assert device.client_fingerprint == valid_sha256

    def test_client_fingerprint_rejects_invalid_length_too_short(self):
        """Test that client_fingerprint rejects SHA256 hash that's too short."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        invalid_hash = "a" * 63  # Too short

        with pytest.raises(ValidationError) as exc_info:
            Device(
                id=DeviceID(uuid4()),
                game_id=game_id,
                client_fingerprint=invalid_hash,
                account_id=account_id,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "client_fingerprint" in str(exc_info.value).lower()

    def test_client_fingerprint_error_message_includes_length(self):
        """Test that fingerprint validation error includes actual length received."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        invalid_hash = "a" * 63  # 63 characters

        with pytest.raises(ValidationError) as exc_info:
            Device(
                id=DeviceID(uuid4()),
                game_id=game_id,
                client_fingerprint=invalid_hash,
                account_id=account_id,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        error_message = str(exc_info.value)
        assert "63" in error_message, f"Error should include length '63', got: {error_message}"

    def test_client_fingerprint_rejects_invalid_length_too_long(self):
        """Test that client_fingerprint rejects SHA256 hash that's too long."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        invalid_hash = "a" * 65  # Too long

        with pytest.raises(ValidationError) as exc_info:
            Device(
                id=DeviceID(uuid4()),
                game_id=game_id,
                client_fingerprint=invalid_hash,
                account_id=account_id,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "client_fingerprint" in str(exc_info.value).lower()

    def test_client_fingerprint_rejects_invalid_characters(self):
        """Test that client_fingerprint rejects non-hex characters."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        invalid_hash = "g" * 64  # 'g' is not a valid hex character

        with pytest.raises(ValidationError) as exc_info:
            Device(
                id=DeviceID(uuid4()),
                game_id=game_id,
                client_fingerprint=invalid_hash,
                account_id=account_id,
                first_seen_at=now,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )

        assert "client_fingerprint" in str(exc_info.value).lower()

    def test_client_fingerprint_normalizes_uppercase_to_lowercase(self):
        """Test that client_fingerprint normalizes uppercase hex to lowercase."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        uppercase_hash = "A" * 64  # Uppercase hex characters

        device = Device(
            id=DeviceID(uuid4()),
            game_id=game_id,
            client_fingerprint=uppercase_hash,
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        # Should be normalized to lowercase
        assert device.client_fingerprint == "a" * 64

    def test_client_fingerprint_normalizes_mixed_case(self):
        """Test that client_fingerprint normalizes mixed case hex to lowercase."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)
        mixed_case_hash = "AaBbCcDd" + "e" * 56  # Mixed case

        device = Device(
            id=DeviceID(uuid4()),
            game_id=game_id,
            client_fingerprint=mixed_case_hash,
            account_id=account_id,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

        # Should be normalized to lowercase
        assert device.client_fingerprint == "aabbccdd" + "e" * 56
