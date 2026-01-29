"""Tests for BoardStateORM model."""

from datetime import UTC, datetime
from uuid import uuid4

from leadr.boards.adapters.orm import BoardStateORM


class TestBoardStateORM:
    """Test suite for BoardStateORM model."""

    def test_create_board_state_orm_with_all_fields(self):
        """Test creating a BoardStateORM with all fields."""
        state_id = uuid4()
        board_id = uuid4()
        identity_id = uuid4()
        now = datetime.now(UTC)

        orm = BoardStateORM(
            id=state_id,
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1000.5,
            aux={"selected_event_id": "sev_abc123", "event_count": 5},
            created_at=now,
            updated_at=now,
        )

        assert orm.id == state_id
        assert orm.board_id == board_id
        assert orm.identity_id == identity_id
        assert orm.primary_value == 1000.5
        assert orm.aux == {"selected_event_id": "sev_abc123", "event_count": 5}
        assert orm.created_at == now
        assert orm.updated_at == now

    def test_create_board_state_orm_with_null_primary_value(self):
        """Test creating a BoardStateORM with NULL primary_value."""
        orm = BoardStateORM(
            id=uuid4(),
            board_id=uuid4(),
            identity_id=uuid4(),
            primary_value=None,
            aux=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert orm.primary_value is None

    def test_board_state_orm_tablename(self):
        """Test that BoardStateORM has correct tablename."""
        assert BoardStateORM.__tablename__ == "board_states"
