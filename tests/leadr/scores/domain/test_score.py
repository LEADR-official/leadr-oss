"""Tests for Score domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.scores.domain.score import Score


class TestScore:
    """Test suite for Score domain entity."""

    def test_create_score_with_required_fields(self):
        """Test creating a score with only required fields."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        assert score.id is not None
        assert score.account_id == account_id
        assert score.game_id == game_id
        assert score.board_id == board_id
        assert score.device_id == device_id
        assert score.player_name == "SpeedRunner99"
        assert score.value == 123.45
        assert score.value_display is None
        assert score.timezone is None
        assert score.country is None
        assert score.city is None
        assert score.created_at is not None
        assert score.updated_at is not None
        assert score.deleted_at is None
        assert score.is_deleted is False

    def test_create_score_with_all_fields(self):
        """Test creating a score with all optional fields."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            value_display="2:03.45",
            timezone="America/New_York",
            country="USA",
            city="New York",
        )

        assert score.value_display == "2:03.45"
        assert score.timezone == "America/New_York"
        assert score.country == "USA"
        assert score.city == "New York"

    def test_create_score_requires_player_name(self):
        """Test that player_name is required."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Score(  # type: ignore[call-arg]
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                value=123.45,
            )

        assert "player_name" in str(exc_info.value)

    def test_create_score_requires_value(self):
        """Test that value is required."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Score(  # type: ignore[call-arg]
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name="SpeedRunner99",
            )

        assert "value" in str(exc_info.value)

    def test_create_score_rejects_empty_player_name(self):
        """Test that empty player_name is rejected."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Score(
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name="",
                value=123.45,
            )

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_create_score_rejects_whitespace_only_player_name(self):
        """Test that whitespace-only player_name is rejected."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            Score(
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name="   ",
                value=123.45,
            )

        assert "cannot be empty" in str(exc_info.value).lower()

    def test_create_score_strips_player_name_whitespace(self):
        """Test that player_name whitespace is stripped."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="  SpeedRunner99  ",
            value=123.45,
        )

        assert score.player_name == "SpeedRunner99"

    def test_account_id_is_immutable(self):
        """Test that account_id cannot be modified after creation."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.account_id = AccountID(uuid4())

        assert "frozen" in str(exc_info.value).lower()

    def test_game_id_is_immutable(self):
        """Test that game_id cannot be modified after creation."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.game_id = GameID(uuid4())

        assert "frozen" in str(exc_info.value).lower()

    def test_board_id_is_immutable(self):
        """Test that board_id cannot be modified after creation."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.board_id = BoardID(uuid4())

        assert "frozen" in str(exc_info.value).lower()

    def test_device_id_is_immutable(self):
        """Test that device_id cannot be modified after creation."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        with pytest.raises(ValidationError) as exc_info:
            score.device_id = DeviceID(uuid4())

        assert "frozen" in str(exc_info.value).lower()

    def test_player_name_is_mutable(self):
        """Test that player_name can be modified after creation."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        score.player_name = "NewName"
        assert score.player_name == "NewName"

    def test_value_is_mutable(self):
        """Test that value can be modified after creation."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        score.value = 200.0
        assert score.value == 200.0

    def test_score_equality(self):
        """Test that scores with same ID are equal."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())
        score_id = ScoreID(uuid4())
        created_at = datetime.now(UTC)

        score1 = Score(
            id=score_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
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
            device_id=device_id,
            player_name="DifferentName",
            value=999.99,
            created_at=created_at,
            updated_at=created_at,
        )

        assert score1 == score2

    def test_score_hash(self):
        """Test that scores can be hashed."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
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
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
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
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
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
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=100,
        )

        assert score.value == 100.0
        assert isinstance(score.value, float)

    def test_value_accepts_negative_numbers(self):
        """Test that value field accepts negative numbers."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=-50.5,
        )

        assert score.value == -50.5

    def test_create_score_with_metadata_dict(self):
        """Test creating a score with metadata as a dictionary."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())
        metadata = {"level": 5, "character": "Warrior", "loadout": ["sword", "shield"]}

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata=metadata,
        )

        assert score.metadata == metadata
        assert score.metadata["level"] == 5  # type: ignore[index]
        assert score.metadata["character"] == "Warrior"  # type: ignore[index]

    def test_create_score_with_metadata_list(self):
        """Test creating a score with metadata as a list."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())
        metadata = [1, 2, 3, 4, 5]

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata=metadata,
        )

        assert score.metadata == metadata
        assert len(score.metadata) == 5  # type: ignore[arg-type]

    def test_create_score_with_metadata_primitive(self):
        """Test creating a score with metadata as a primitive value."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        # Test with string
        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata="test-string",
        )
        assert score.metadata == "test-string"

        # Test with number
        score2 = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata=42,
        )
        assert score2.metadata == 42

    def test_create_score_with_null_metadata(self):
        """Test creating a score with null metadata (default)."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        assert score.metadata is None

    def test_create_score_with_oversized_metadata(self):
        """Test that oversized metadata raises validation error."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        # Create metadata that exceeds 1KB when serialized
        # Each key-value pair is roughly 20-30 bytes, so we need ~40-50 items
        large_metadata = {f"key{i}": f"value{i}" for i in range(100)}

        with pytest.raises(ValidationError) as exc_info:
            Score(
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                device_id=device_id,
                player_name="SpeedRunner99",
                value=123.45,
                metadata=large_metadata,
            )

        assert "metadata" in str(exc_info.value).lower()
        assert "limit" in str(exc_info.value).lower()

    def test_metadata_is_mutable(self):
        """Test that metadata can be modified after creation."""
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        device_id = DeviceID(uuid4())

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name="SpeedRunner99",
            value=123.45,
            metadata={"initial": "data"},
        )

        new_metadata = {"updated": "data", "extra": 123}
        score.metadata = new_metadata
        assert score.metadata == new_metadata
