"""Tests for JamCode domain model."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.registration.domain.jam_code import JamCode


class TestJamCode:
    """Test suite for JamCode domain model."""

    def test_create_jam_code_with_valid_data(self):
        """Test creating a jam code with all required fields."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=30)

        code = JamCode(
            code="GAMEJAM2025",
            description="Game Jam 2025 Promo Code",
            features={"cli_template": "godot", "score_limit": 10000},
            max_uses=100,
            current_uses=0,
            active=True,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )

        assert code.code == "GAMEJAM2025"
        assert code.description == "Game Jam 2025 Promo Code"
        assert code.features == {"cli_template": "godot", "score_limit": 10000}
        assert code.max_uses == 100
        assert code.current_uses == 0
        assert code.active is True
        assert code.expires_at == expires_at

    def test_create_jam_code_defaults(self):
        """Test that jam code has proper default values."""
        code = JamCode(
            code="TEST2025",
            description="Test Code",
        )

        assert code.features == {}
        assert code.max_uses is None
        assert code.current_uses == 0
        assert code.active is True
        assert code.expires_at is None

    def test_code_required(self):
        """Test that code is required."""
        with pytest.raises(ValidationError) as exc_info:
            JamCode(  # type: ignore[call-arg]
                description="Test Code",
            )

        assert "code" in str(exc_info.value)

    def test_description_required(self):
        """Test that description is required."""
        with pytest.raises(ValidationError) as exc_info:
            JamCode(  # type: ignore[call-arg]
                code="TEST2025",
            )

        assert "description" in str(exc_info.value)

    def test_code_normalizes_to_uppercase(self):
        """Test that code normalizes to uppercase."""
        code = JamCode(
            code="gamejam2025",  # Lowercase input
            description="Test",
        )

        assert code.code == "GAMEJAM2025"

    def test_code_accepts_alphanumeric(self):
        """Test that code accepts alphanumeric characters."""
        valid_codes = ["GAMEJAM2025", "CODE123", "TEST", "12345", "ABC123XYZ"]

        for valid_code in valid_codes:
            code = JamCode(
                code=valid_code,
                description="Test",
            )
            assert code.code == valid_code.upper()

    def test_code_rejects_special_characters(self):
        """Test that code rejects special characters."""
        invalid_codes = ["GAME-JAM", "CODE@2025", "TEST CODE", "JAM_2025"]

        for invalid_code in invalid_codes:
            with pytest.raises(ValidationError) as exc_info:
                JamCode(
                    code=invalid_code,
                    description="Test",
                )
            assert "code" in str(exc_info.value).lower()

    def test_code_min_length(self):
        """Test that code enforces minimum length of 3 characters."""
        with pytest.raises(ValidationError) as exc_info:
            JamCode(
                code="AB",  # Only 2 characters
                description="Test",
            )

        assert "code" in str(exc_info.value).lower()

    def test_code_max_length(self):
        """Test that code enforces maximum length of 50 characters."""
        with pytest.raises(ValidationError) as exc_info:
            JamCode(
                code="A" * 51,  # 51 characters
                description="Test",
            )

        assert "code" in str(exc_info.value).lower()

    def test_is_expired_when_expiration_in_past(self):
        """Test that is_expired returns True when expires_at is in the past."""
        past_date = datetime.now(UTC) - timedelta(days=1)

        code = JamCode(
            code="EXPIRED2024",
            description="Expired Code",
            expires_at=past_date,
        )

        assert code.is_expired() is True

    def test_is_not_expired_when_expiration_in_future(self):
        """Test that is_expired returns False when expires_at is in the future."""
        future_date = datetime.now(UTC) + timedelta(days=30)

        code = JamCode(
            code="FUTURE2025",
            description="Future Code",
            expires_at=future_date,
        )

        assert code.is_expired() is False

    def test_is_not_expired_when_no_expiration(self):
        """Test that is_expired returns False when expires_at is None."""
        code = JamCode(
            code="NOEXPIRY",
            description="No Expiry Code",
            expires_at=None,
        )

        assert code.is_expired() is False

    def test_has_uses_remaining_with_unlimited_uses(self):
        """Test that has_uses_remaining returns True when max_uses is None."""
        code = JamCode(
            code="UNLIMITED",
            description="Unlimited Uses",
            max_uses=None,
            current_uses=1000,  # Even with high current_uses
        )

        assert code.has_uses_remaining() is True

    def test_has_uses_remaining_with_uses_left(self):
        """Test that has_uses_remaining returns True when uses remain."""
        code = JamCode(
            code="LIMITED",
            description="Limited Uses",
            max_uses=100,
            current_uses=50,
        )

        assert code.has_uses_remaining() is True

    def test_has_no_uses_remaining_when_exhausted(self):
        """Test that has_uses_remaining returns False when uses exhausted."""
        code = JamCode(
            code="EXHAUSTED",
            description="Exhausted Code",
            max_uses=100,
            current_uses=100,
        )

        assert code.has_uses_remaining() is False

    def test_has_no_uses_remaining_when_over_limit(self):
        """Test that has_uses_remaining returns False when over limit."""
        code = JamCode(
            code="OVERLIMIT",
            description="Over Limit Code",
            max_uses=100,
            current_uses=101,
        )

        assert code.has_uses_remaining() is False

    def test_is_valid_when_active_not_expired_with_uses(self):
        """Test that is_valid returns True when code is active, not expired, with uses."""
        future_date = datetime.now(UTC) + timedelta(days=30)

        code = JamCode(
            code="VALID2025",
            description="Valid Code",
            active=True,
            expires_at=future_date,
            max_uses=100,
            current_uses=50,
        )

        assert code.is_valid() is True

    def test_is_not_valid_when_inactive(self):
        """Test that is_valid returns False when code is inactive."""
        future_date = datetime.now(UTC) + timedelta(days=30)

        code = JamCode(
            code="INACTIVE",
            description="Inactive Code",
            active=False,
            expires_at=future_date,
            max_uses=100,
            current_uses=50,
        )

        assert code.is_valid() is False

    def test_is_not_valid_when_expired(self):
        """Test that is_valid returns False when code is expired."""
        past_date = datetime.now(UTC) - timedelta(days=1)

        code = JamCode(
            code="EXPIRED",
            description="Expired Code",
            active=True,
            expires_at=past_date,
            max_uses=100,
            current_uses=50,
        )

        assert code.is_valid() is False

    def test_is_not_valid_when_no_uses_remaining(self):
        """Test that is_valid returns False when no uses remaining."""
        future_date = datetime.now(UTC) + timedelta(days=30)

        code = JamCode(
            code="NOUSES",
            description="No Uses Code",
            active=True,
            expires_at=future_date,
            max_uses=100,
            current_uses=100,
        )

        assert code.is_valid() is False

    def test_increment_uses(self):
        """Test incrementing the usage count."""
        code = JamCode(
            code="INCREMENT",
            description="Increment Test",
            max_uses=100,
            current_uses=50,
        )

        assert code.current_uses == 50

        code.increment_uses()

        assert code.current_uses == 51

    def test_increment_uses_multiple_times(self):
        """Test incrementing the usage count multiple times."""
        code = JamCode(
            code="MULTI",
            description="Multi Increment Test",
            max_uses=100,
            current_uses=0,
        )

        code.increment_uses()
        code.increment_uses()
        code.increment_uses()

        assert code.current_uses == 3

    def test_deactivate(self):
        """Test deactivating a code."""
        code = JamCode(
            code="DEACTIVATE",
            description="Deactivate Test",
            active=True,
        )

        assert code.active is True

        code.deactivate()

        assert code.active is False

    def test_activate(self):
        """Test activating a code."""
        code = JamCode(
            code="ACTIVATE",
            description="Activate Test",
            active=False,
        )

        assert code.active is False

        code.activate()

        assert code.active is True

    def test_jam_code_equality_based_on_id(self):
        """Test that jam code equality is based on ID."""
        code_id = uuid4()
        now = datetime.now(UTC)

        code1 = JamCode(
            id=code_id,
            code="CODE1",
            description="First",
            created_at=now,
            updated_at=now,
        )

        code2 = JamCode(
            id=code_id,
            code="CODE2",
            description="Second",
            created_at=now,
            updated_at=now,
        )

        assert code1 == code2

    def test_jam_code_inequality_different_ids(self):
        """Test that jam codes with different IDs are not equal."""
        code1 = JamCode(
            code="CODE1",
            description="First",
        )

        code2 = JamCode(
            code="CODE1",
            description="First",
        )

        assert code1 != code2

    def test_get_feature(self):
        """Test getting a feature value from the features dict."""
        code = JamCode(
            code="FEATURES",
            description="Features Test",
            features={"cli_template": "godot", "score_limit": 10000},
        )

        assert code.get_feature("cli_template") == "godot"
        assert code.get_feature("score_limit") == 10000
        assert code.get_feature("nonexistent") is None

    def test_get_feature_with_default(self):
        """Test getting a feature value with a default."""
        code = JamCode(
            code="DEFAULT",
            description="Default Test",
            features={"cli_template": "godot"},
        )

        assert code.get_feature("nonexistent", "default_value") == "default_value"
        assert code.get_feature("cli_template", "default_value") == "godot"
