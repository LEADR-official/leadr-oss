"""Tests for BoardState domain model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from leadr.boards.domain.board_state import BoardState
from leadr.common.domain.ids import BoardID, BoardStateID, IdentityID, ScoreEventID


class TestBoardState:
    """Test suite for BoardState domain model."""

    def test_create_board_state_with_all_fields(self):
        """Test creating a board state with all fields including optional ones."""
        state_id = BoardStateID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        now = datetime.now(UTC)

        state = BoardState(
            id=state_id,
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1000.5,
            aux={"selected_event_id": "sev_abc123", "event_count": 5},
            created_at=now,
            updated_at=now,
        )

        assert state.id == state_id
        assert state.board_id == board_id
        assert state.identity_id == identity_id
        assert state.primary_value == 1000.5
        assert state.aux == {"selected_event_id": "sev_abc123", "event_count": 5}
        assert state.created_at == now
        assert state.updated_at == now

    def test_create_board_state_with_required_fields_only(self):
        """Test creating a board state with only required fields."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
        )

        # Should have auto-generated ID
        assert state.id is not None
        assert isinstance(state.id, BoardStateID)
        assert state.board_id == board_id
        assert state.identity_id == identity_id
        # Defaults
        assert state.primary_value is None
        assert state.aux is None
        # Auto-generated timestamps
        assert state.created_at is not None
        assert state.updated_at is not None

    def test_create_board_state_with_null_primary_value(self):
        """Test creating a board state with NULL primary_value (not rankable)."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=None,
        )

        assert state.primary_value is None

    def test_create_board_state_with_zero_primary_value(self):
        """Test creating a board state with zero primary_value."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=0.0,
        )

        assert state.primary_value == 0.0

    def test_create_board_state_with_negative_primary_value(self):
        """Test creating a board state with negative primary_value."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=-500.0,
        )

        assert state.primary_value == -500.0

    def test_board_state_board_id_required(self):
        """Test that board_id is required."""
        identity_id = IdentityID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            BoardState(  # type: ignore[call-arg]
                identity_id=identity_id,
            )

        assert "board_id" in str(exc_info.value)

    def test_board_state_identity_id_required(self):
        """Test that identity_id is required."""
        board_id = BoardID(uuid4())

        with pytest.raises(ValidationError) as exc_info:
            BoardState(  # type: ignore[call-arg]
                board_id=board_id,
            )

        assert "identity_id" in str(exc_info.value)

    def test_board_state_equality_based_on_id(self):
        """Test that board state equality is based on ID."""
        state_id = BoardStateID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state1 = BoardState(
            id=state_id,
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        state2 = BoardState(
            id=state_id,
            board_id=BoardID(uuid4()),  # Different board
            identity_id=IdentityID(uuid4()),  # Different identity
            primary_value=200.0,  # Different value
        )

        assert state1 == state2

    def test_board_state_inequality_different_ids(self):
        """Test that board states with different IDs are not equal."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state1 = BoardState(
            id=BoardStateID(uuid4()),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        state2 = BoardState(
            id=BoardStateID(uuid4()),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,  # Same value, different ID
        )

        assert state1 != state2

    def test_board_state_is_hashable(self):
        """Test that board state can be used in sets and as dict keys."""
        state_id = BoardStateID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            id=state_id,
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        # Should be hashable
        state_set = {state}  # type: ignore[var-annotated]
        assert state in state_set

        # Should work as dict key
        state_dict = {state: "value"}  # type: ignore[dict-item]
        assert state_dict[state] == "value"

    def test_board_state_immutability_of_id(self):
        """Test that board state ID cannot be changed after creation."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        new_id = BoardStateID(uuid4())

        with pytest.raises(ValidationError):
            state.id = new_id  # type: ignore[misc]

    def test_board_state_immutability_of_board_id(self):
        """Test that board_id cannot be changed after creation."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        new_board_id = BoardID(uuid4())

        with pytest.raises(ValidationError):
            state.board_id = new_board_id  # type: ignore[misc]

    def test_board_state_immutability_of_identity_id(self):
        """Test that identity_id cannot be changed after creation."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        new_identity_id = IdentityID(uuid4())

        with pytest.raises(ValidationError):
            state.identity_id = new_identity_id  # type: ignore[misc]

    def test_board_state_primary_value_is_mutable(self):
        """Test that primary_value can be updated."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        state.primary_value = 200.0
        assert state.primary_value == 200.0

    def test_board_state_aux_is_mutable(self):
        """Test that aux can be updated."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            aux={"event_count": 1},
        )

        state.aux = {"event_count": 2, "new_field": "value"}
        assert state.aux == {"event_count": 2, "new_field": "value"}

    def test_board_state_soft_delete(self):
        """Test that board state can be soft-deleted."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        assert state.is_deleted is False
        assert state.deleted_at is None

        state.soft_delete()

        assert state.is_deleted is True
        assert state.deleted_at is not None

    def test_board_state_restore(self):
        """Test that soft-deleted board state can be restored."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )

        state.soft_delete()
        assert state.is_deleted is True

        state.restore()
        assert state.is_deleted is False
        assert state.deleted_at is None


class TestBoardStateAuxData:
    """Test suite for BoardState aux data handling."""

    def test_run_identity_aux_data(self):
        """Test aux data structure for RUN_IDENTITY boards."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        event_id = ScoreEventID(uuid4())

        aux = {
            "selected_event_id": str(event_id),
            "event_count": 3,
        }

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1500.0,
            aux=aux,
        )

        assert state.aux is not None
        assert state.aux["selected_event_id"] == str(event_id)
        assert state.aux["event_count"] == 3

    def test_counter_aux_data(self):
        """Test aux data structure for COUNTER boards."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        event_id = ScoreEventID(uuid4())

        aux = {
            "event_count": 25,
            "last_event_id": str(event_id),
        }

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=500.0,
            aux=aux,
        )

        assert state.aux is not None
        assert state.aux["event_count"] == 25
        assert state.aux["last_event_id"] == str(event_id)

    def test_ratio_aux_data(self):
        """Test aux data structure for RATIO boards."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        aux = {
            "numerator_value": 75.0,
            "denominator_value": 100.0,
        }

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=0.75,  # 75/100
            aux=aux,
        )

        assert state.aux is not None
        assert state.aux["numerator_value"] == 75.0
        assert state.aux["denominator_value"] == 100.0

    def test_aux_data_can_be_empty_dict(self):
        """Test that aux can be an empty dict."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            aux={},
        )

        assert state.aux == {}

    def test_aux_data_can_be_none(self):
        """Test that aux can be None."""
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            aux=None,
        )

        assert state.aux is None
