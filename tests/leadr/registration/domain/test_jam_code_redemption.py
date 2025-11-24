"""Tests for JamCodeRedemption domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.common.domain.ids import AccountID
from leadr.registration.domain.jam_code_redemption import JamCodeRedemption


class TestJamCodeRedemption:
    """Test suite for JamCodeRedemption domain model."""

    def test_create_jam_code_redemption_with_valid_data(self):
        """Test creating a jam code redemption with all required fields."""
        now = datetime.now(UTC)
        jam_code_id = uuid4()
        account_id = AccountID()

        redemption = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
            redeemed_at=now,
            meta={"cli_template": "godot", "user_agent": "leadr-cli/1.0"},
            created_at=now,
            updated_at=now,
        )

        assert redemption.jam_code_id == jam_code_id
        assert redemption.account_id == account_id
        assert redemption.redeemed_at == now
        assert redemption.meta == {"cli_template": "godot", "user_agent": "leadr-cli/1.0"}

    def test_create_jam_code_redemption_with_empty_meta(self):
        """Test creating a jam code redemption with empty meta."""
        now = datetime.now(UTC)
        jam_code_id = uuid4()
        account_id = AccountID()

        redemption = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
            redeemed_at=now,
            meta={},
            created_at=now,
            updated_at=now,
        )

        assert redemption.meta == {}

    def test_create_jam_code_redemption_defaults_to_current_time(self):
        """Test that redeemed_at defaults to current time if not provided."""
        jam_code_id = uuid4()
        account_id = AccountID()

        redemption = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
        )

        # Should be set to current time (within 1 second tolerance)
        assert (datetime.now(UTC) - redemption.redeemed_at).total_seconds() < 1

    def test_create_jam_code_redemption_defaults_empty_meta(self):
        """Test that meta defaults to empty dict if not provided."""
        jam_code_id = uuid4()
        account_id = AccountID()

        redemption = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
        )

        assert redemption.meta == {}

    def test_jam_code_id_required(self):
        """Test that jam_code_id is required."""
        account_id = AccountID()

        with pytest.raises(ValidationError) as exc_info:
            JamCodeRedemption(  # type: ignore[call-arg]
                account_id=account_id,
            )

        assert "jam_code_id" in str(exc_info.value)

    def test_account_id_required(self):
        """Test that account_id is required."""
        jam_code_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            JamCodeRedemption(  # type: ignore[call-arg]
                jam_code_id=jam_code_id,
            )

        assert "account_id" in str(exc_info.value)

    def test_get_meta_value(self):
        """Test getting a meta value from the meta dict."""
        jam_code_id = uuid4()
        account_id = AccountID()

        redemption = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
            meta={"cli_template": "godot", "score_limit": 10000},
        )

        assert redemption.get_meta("cli_template") == "godot"
        assert redemption.get_meta("score_limit") == 10000
        assert redemption.get_meta("nonexistent") is None

    def test_get_meta_value_with_default(self):
        """Test getting a meta value with a default."""
        jam_code_id = uuid4()
        account_id = AccountID()

        redemption = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
            meta={"cli_template": "godot"},
        )

        assert redemption.get_meta("nonexistent", "default_value") == "default_value"
        assert redemption.get_meta("cli_template", "default_value") == "godot"

    def test_jam_code_redemption_equality_based_on_id(self):
        """Test that jam code redemption equality is based on ID."""
        redemption_id = uuid4()
        jam_code_id = uuid4()
        account_id = AccountID()
        now = datetime.now(UTC)

        redemption1 = JamCodeRedemption(
            id=redemption_id,
            jam_code_id=jam_code_id,
            account_id=account_id,
            redeemed_at=now,
            created_at=now,
            updated_at=now,
        )

        redemption2 = JamCodeRedemption(
            id=redemption_id,
            jam_code_id=uuid4(),  # Different jam_code_id
            account_id=AccountID(),  # Different account_id
            redeemed_at=now,
            created_at=now,
            updated_at=now,
        )

        assert redemption1 == redemption2

    def test_jam_code_redemption_inequality_different_ids(self):
        """Test that redemptions with different IDs are not equal."""
        jam_code_id = uuid4()
        account_id = AccountID()

        redemption1 = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
        )

        redemption2 = JamCodeRedemption(
            jam_code_id=jam_code_id,
            account_id=account_id,
        )

        assert redemption1 != redemption2
