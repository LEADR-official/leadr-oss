"""Tests for RunEntry domain model."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.boards.domain.run_entry import RunEntry
from leadr.common.domain.ids import BoardID, IdentityID, RunEntryID, ScoreEventID


class TestRunEntryCreation:
    """Tests for RunEntry instantiation."""

    def test_create_run_entry_with_required_fields(self) -> None:
        """Creating a run entry with required fields succeeds."""
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()
        primary_value = 1000.0

        entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=primary_value,
        )

        assert entry.board_id == board_id
        assert entry.identity_id == identity_id
        assert entry.score_event_id == score_event_id
        assert entry.primary_value == primary_value
        assert isinstance(entry.id, RunEntryID)
        assert entry.created_at is not None
        assert entry.updated_at is not None
        assert entry.deleted_at is None

    def test_create_run_entry_with_all_fields(self) -> None:
        """Creating a run entry with all fields succeeds."""
        entry_id = RunEntryID()
        board_id = BoardID()
        identity_id = IdentityID()
        score_event_id = ScoreEventID()
        primary_value = 2500.5
        now = datetime.now(UTC)

        entry = RunEntry(
            id=entry_id,
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=primary_value,
            created_at=now,
            updated_at=now,
        )

        assert entry.id == entry_id
        assert entry.board_id == board_id
        assert entry.identity_id == identity_id
        assert entry.score_event_id == score_event_id
        assert entry.primary_value == primary_value
        assert entry.created_at == now
        assert entry.updated_at == now

    def test_create_run_entry_auto_generates_id(self) -> None:
        """Run entry auto-generates ID when not provided."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        assert entry.id is not None
        assert isinstance(entry.id, RunEntryID)
        assert str(entry.id).startswith("run_")

    def test_create_run_entry_auto_generates_timestamps(self) -> None:
        """Run entry auto-generates timestamps when not provided."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        assert entry.created_at is not None
        assert entry.updated_at is not None
        assert entry.created_at.tzinfo is not None
        assert entry.updated_at.tzinfo is not None

    def test_create_run_entry_requires_board_id(self) -> None:
        """Creating a run entry without board_id raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RunEntry(
                identity_id=IdentityID(),
                score_event_id=ScoreEventID(),
                primary_value=100.0,
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("board_id",) for e in errors)

    def test_create_run_entry_requires_identity_id(self) -> None:
        """Creating a run entry without identity_id raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RunEntry(
                board_id=BoardID(),
                score_event_id=ScoreEventID(),
                primary_value=100.0,
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("identity_id",) for e in errors)

    def test_create_run_entry_requires_score_event_id(self) -> None:
        """Creating a run entry without score_event_id raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RunEntry(
                board_id=BoardID(),
                identity_id=IdentityID(),
                primary_value=100.0,
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("score_event_id",) for e in errors)

    def test_create_run_entry_requires_primary_value(self) -> None:
        """Creating a run entry without primary_value raises error."""
        with pytest.raises(ValidationError) as exc_info:
            RunEntry(
                board_id=BoardID(),
                identity_id=IdentityID(),
                score_event_id=ScoreEventID(),
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("primary_value",) for e in errors)


class TestRunEntryImmutability:
    """Tests for RunEntry field immutability."""

    def test_id_is_immutable(self) -> None:
        """Run entry ID cannot be changed after creation."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        with pytest.raises(ValidationError):
            entry.id = RunEntryID()

    def test_board_id_is_immutable(self) -> None:
        """Run entry board_id cannot be changed after creation."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        with pytest.raises(ValidationError):
            entry.board_id = BoardID()

    def test_identity_id_is_immutable(self) -> None:
        """Run entry identity_id cannot be changed after creation."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        with pytest.raises(ValidationError):
            entry.identity_id = IdentityID()

    def test_score_event_id_is_immutable(self) -> None:
        """Run entry score_event_id cannot be changed after creation."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        with pytest.raises(ValidationError):
            entry.score_event_id = ScoreEventID()

    def test_primary_value_is_immutable(self) -> None:
        """Run entry primary_value cannot be changed after creation."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        with pytest.raises(ValidationError):
            entry.primary_value = 200.0


class TestRunEntryPrimaryValue:
    """Tests for RunEntry primary_value handling."""

    def test_primary_value_as_integer(self) -> None:
        """Primary value can be an integer."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=1000,
        )

        assert entry.primary_value == 1000.0

    def test_primary_value_as_float(self) -> None:
        """Primary value can be a float."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=1000.5,
        )

        assert entry.primary_value == 1000.5

    def test_primary_value_as_negative(self) -> None:
        """Primary value can be negative."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=-500.0,
        )

        assert entry.primary_value == -500.0

    def test_primary_value_as_zero(self) -> None:
        """Primary value can be zero."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=0.0,
        )

        assert entry.primary_value == 0.0


class TestRunEntrySoftDelete:
    """Tests for RunEntry soft delete behavior."""

    def test_deleted_at_defaults_to_none(self) -> None:
        """deleted_at defaults to None."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        assert entry.deleted_at is None

    def test_is_deleted_returns_false_when_not_deleted(self) -> None:
        """is_deleted returns False when deleted_at is None."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        assert entry.is_deleted is False

    def test_is_deleted_returns_true_when_deleted(self) -> None:
        """is_deleted returns True when deleted_at is set."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
            deleted_at=datetime.now(UTC),
        )

        assert entry.is_deleted is True

    def test_soft_delete_sets_deleted_at(self) -> None:
        """soft_delete sets the deleted_at timestamp."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        entry.soft_delete()

        assert entry.deleted_at is not None
        assert entry.is_deleted is True


class TestRunEntrySerialization:
    """Tests for RunEntry serialization."""

    def test_model_dump_includes_all_fields(self) -> None:
        """model_dump includes all fields."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        data = entry.model_dump()

        assert "id" in data
        assert "board_id" in data
        assert "identity_id" in data
        assert "score_event_id" in data
        assert "primary_value" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "deleted_at" in data

    def test_id_serializes_as_string(self) -> None:
        """ID serializes as prefixed string."""
        entry = RunEntry(
            board_id=BoardID(),
            identity_id=IdentityID(),
            score_event_id=ScoreEventID(),
            primary_value=100.0,
        )

        data = entry.model_dump(mode="json")

        assert isinstance(data["id"], str)
        assert data["id"].startswith("run_")
