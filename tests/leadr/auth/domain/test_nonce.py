"""Tests for Nonce domain entity."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from leadr.auth.domain.nonce import Nonce, NonceStatus


class TestNonceEntity:
    """Test suite for Nonce domain entity."""

    def test_create_nonce_with_required_fields(self):
        """Test creating a nonce with required fields."""
        device_id = uuid4()
        nonce_value = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(seconds=60)

        nonce = Nonce(
            device_id=device_id,
            nonce_value=nonce_value,
            expires_at=expires_at,
        )

        assert nonce.device_id == device_id
        assert nonce.nonce_value == nonce_value
        assert nonce.expires_at == expires_at
        assert nonce.used_at is None
        assert nonce.status == NonceStatus.PENDING
        assert nonce.id is not None
        assert nonce.created_at is not None
        assert nonce.updated_at is not None

    def test_create_nonce_with_all_fields(self):
        """Test creating a nonce with all fields specified."""
        device_id = uuid4()
        nonce_value = str(uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=60)
        used_at = now + timedelta(seconds=30)

        nonce = Nonce(
            device_id=device_id,
            nonce_value=nonce_value,
            expires_at=expires_at,
            used_at=used_at,
            status=NonceStatus.USED,
        )

        assert nonce.device_id == device_id
        assert nonce.nonce_value == nonce_value
        assert nonce.expires_at == expires_at
        assert nonce.used_at == used_at
        assert nonce.status == NonceStatus.USED

    def test_nonce_status_defaults_to_pending(self):
        """Test that nonce status defaults to PENDING."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        assert nonce.status == NonceStatus.PENDING

    def test_is_expired_returns_false_for_valid_nonce(self):
        """Test that is_expired returns False for non-expired nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        assert nonce.is_expired() is False

    def test_is_expired_returns_true_for_expired_nonce(self):
        """Test that is_expired returns True for expired nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),  # Expired
        )

        assert nonce.is_expired() is True

    def test_is_expired_returns_true_at_exact_expiry(self):
        """Test that is_expired returns True at exact expiry time."""
        now = datetime.now(UTC)
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=now,
        )

        # Advance time slightly to ensure we're at or past expiry
        assert nonce.is_expired() is True

    def test_is_used_returns_false_for_pending_nonce(self):
        """Test that is_used returns False for pending nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.PENDING,
        )

        assert nonce.is_used() is False

    def test_is_used_returns_true_for_used_nonce(self):
        """Test that is_used returns True for used nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.USED,
        )

        assert nonce.is_used() is True

    def test_is_used_returns_false_for_expired_nonce(self):
        """Test that is_used returns False for expired nonce (not used)."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.EXPIRED,
        )

        assert nonce.is_used() is False

    def test_is_valid_returns_true_for_pending_unexpired_nonce(self):
        """Test that is_valid returns True for pending, unexpired nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.PENDING,
        )

        assert nonce.is_valid() is True

    def test_is_valid_returns_false_for_used_nonce(self):
        """Test that is_valid returns False for used nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.USED,
        )

        assert nonce.is_valid() is False

    def test_is_valid_returns_false_for_expired_pending_nonce(self):
        """Test that is_valid returns False for expired pending nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
            status=NonceStatus.PENDING,
        )

        assert nonce.is_valid() is False

    def test_is_valid_returns_false_for_expired_status_nonce(self):
        """Test that is_valid returns False for nonce with EXPIRED status."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.EXPIRED,
        )

        assert nonce.is_valid() is False

    def test_mark_used_sets_status_and_timestamp(self):
        """Test that mark_used sets status to USED and sets used_at."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        before = datetime.now(UTC)
        nonce.mark_used()
        after = datetime.now(UTC)

        assert nonce.status == NonceStatus.USED
        assert nonce.used_at is not None
        assert before <= nonce.used_at <= after

    def test_mark_used_raises_error_for_already_used_nonce(self):
        """Test that mark_used raises ValueError for already used nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.USED,
            used_at=datetime.now(UTC),
        )

        with pytest.raises(ValueError, match="Cannot mark invalid nonce as used"):
            nonce.mark_used()

    def test_mark_used_raises_error_for_expired_nonce(self):
        """Test that mark_used raises ValueError for expired nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
            status=NonceStatus.PENDING,
        )

        with pytest.raises(ValueError, match="Cannot mark invalid nonce as used"):
            nonce.mark_used()

    def test_mark_used_raises_error_for_expired_status_nonce(self):
        """Test that mark_used raises ValueError for nonce with EXPIRED status."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.EXPIRED,
        )

        with pytest.raises(ValueError, match="Cannot mark invalid nonce as used"):
            nonce.mark_used()

    def test_mark_expired_sets_status_for_pending_nonce(self):
        """Test that mark_expired sets status to EXPIRED for pending nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
            status=NonceStatus.PENDING,
        )

        nonce.mark_expired()

        assert nonce.status == NonceStatus.EXPIRED

    def test_mark_expired_does_not_change_used_nonce(self):
        """Test that mark_expired does not change status of used nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.USED,
            used_at=datetime.now(UTC),
        )

        nonce.mark_expired()

        # Status should remain USED
        assert nonce.status == NonceStatus.USED

    def test_mark_expired_does_not_change_already_expired_nonce(self):
        """Test that mark_expired is idempotent for already expired nonce."""
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=str(uuid4()),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=NonceStatus.EXPIRED,
        )

        nonce.mark_expired()

        assert nonce.status == NonceStatus.EXPIRED

    def test_nonce_value_can_be_uuid_string(self):
        """Test that nonce_value accepts UUID string format."""
        nonce_value = str(uuid4())
        nonce = Nonce(
            device_id=uuid4(),
            nonce_value=nonce_value,
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )

        assert nonce.nonce_value == nonce_value
        assert len(nonce.nonce_value) == 36  # UUID string length
