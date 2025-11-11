"""Tests for Score domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.scores.domain.score import Score


class TestScore:
    """Test suite for Score domain entity."""

    def test_create_score_with_required_fields(self):
        """Test creating a score with only required fields."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        assert score.id is not None
        assert score.account_id == account_id
        assert score.game_id == game_id
        assert score.board_id == board_id
        assert score.user_id == user_id
        assert score.player_name == "SpeedRunner99"
        assert score.value == 123.45
        assert score.value_display is None
        assert score.filter_timezone is None
        assert score.filter_country is None
        assert score.filter_city is None
        assert score.created_at is not None
        assert score.updated_at is not None
        assert score.deleted_at is None
        assert score.is_deleted is False

    def test_create_score_with_all_fields(self):
        """Test creating a score with all optional fields."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
            value_display="2:03.45",
            filter_timezone="America/New_York",
            filter_country="USA",
            filter_city="New York",
        )

        assert score.value_display == "2:03.45"
        assert score.filter_timezone == "America/New_York"
        assert score.filter_country == "USA"
        assert score.filter_city == "New York"

    def test_create_score_requires_player_name(self):
        """Test that player_name is required."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            Score(  # type: ignore[call-arg]
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                user_id=user_id,
                value=123.45,
            )

        assert "player_name" in str(exc_info.value)

    def test_create_score_requires_value(self):
        """Test that value is required."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            Score(  # type: ignore[call-arg]
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                user_id=user_id,
                player_name="SpeedRunner99",
            )

        assert "value" in str(exc_info.value)

    def test_create_score_rejects_empty_player_name(self):
        """Test that empty player_name is rejected."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            Score(
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                user_id=user_id,
                player_name="",
                value=123.45,
            )

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_create_score_rejects_whitespace_only_player_name(self):
        """Test that whitespace-only player_name is rejected."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            Score(
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                user_id=user_id,
                player_name="   ",
                value=123.45,
            )

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_create_score_strips_player_name_whitespace(self):
        """Test that player_name whitespace is stripped."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="  SpeedRunner99  ",
            value=123.45,
        )

        assert score.player_name == "SpeedRunner99"

    def test_account_id_is_immutable(self):
        """Test that account_id cannot be modified after creation."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.account_id = uuid4()

        assert "frozen" in str(exc_info.value).lower()

    def test_game_id_is_immutable(self):
        """Test that game_id cannot be modified after creation."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.game_id = uuid4()

        assert "frozen" in str(exc_info.value).lower()

    def test_board_id_is_immutable(self):
        """Test that board_id cannot be modified after creation."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.board_id = uuid4()

        assert "frozen" in str(exc_info.value).lower()

    def test_user_id_is_immutable(self):
        """Test that user_id cannot be modified after creation."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.user_id = uuid4()

        assert "frozen" in str(exc_info.value).lower()

    def test_player_name_is_mutable(self):
        """Test that player_name can be modified after creation."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        score.player_name = "NewName"
        assert score.player_name == "NewName"

    def test_value_is_mutable(self):
        """Test that value can be modified after creation."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        score.value = 200.0
        assert score.value == 200.0

    def test_score_equality(self):
        """Test that scores with same ID are equal."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()
        score_id = uuid4()
        created_at = datetime.now(UTC)

        score1 = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
            created_at=created_at,
            updated_at=created_at,
        )

        score2 = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="DifferentName",
            value=999.99,
            created_at=created_at,
            updated_at=created_at,
        )

        assert score1 == score2

    def test_score_hash(self):
        """Test that scores can be hashed."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Should not raise
        hash(score)

        # Test in set
        score_set = {score}  # type: ignore[var-annotated]
        assert score in score_set

    def test_soft_delete_score(self):
        """Test soft-deleting a score."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        assert score.is_deleted is False
        assert score.deleted_at is None

        score.soft_delete()

        assert score.is_deleted is True
        assert score.deleted_at is not None
        assert isinstance(score.deleted_at, datetime)

    def test_restore_score(self):
        """Test restoring a soft-deleted score."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        score.soft_delete()
        assert score.is_deleted is True

        score.restore()

        assert score.is_deleted is False
        assert score.deleted_at is None

    def test_value_accepts_integers(self):
        """Test that value field accepts integers (converted to float)."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=100,
        )

        assert score.value == 100.0
        assert isinstance(score.value, float)

    def test_value_accepts_negative_numbers(self):
        """Test that value field accepts negative numbers."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        user_id = uuid4()

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name="SpeedRunner99",
            value=-50.5,
        )

        assert score.value == -50.5
