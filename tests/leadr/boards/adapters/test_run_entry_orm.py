"""Tests for RunEntryORM model."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from leadr.accounts.adapters.orm import AccountORM
from leadr.auth.adapters.orm import IdentityORM
from leadr.boards.adapters.orm import BoardORM, RunEntryORM
from leadr.games.adapters.orm import GameORM
from leadr.scores.adapters.orm import ScoreEventORM


@pytest.mark.asyncio
class TestRunEntryORM:
    """Tests for RunEntryORM model."""

    async def test_run_entry_orm_tablename(self, db_session) -> None:
        """ORM tablename is correct."""
        assert RunEntryORM.__tablename__ == "run_entries"

    async def test_create_run_entry_orm_with_all_fields(self, db_session) -> None:
        """Creating a run entry with all fields succeeds."""
        # Create required parent entities
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        identity_id = uuid4()
        score_event_id = uuid4()
        now = datetime.now(UTC)

        account = AccountORM(id=account_id, name="Test", slug="test")
        db_session.add(account)
        await db_session.flush()

        game = GameORM(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        db_session.add(game)
        await db_session.flush()

        board = BoardORM(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            short_code="TEST01",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add(board)
        await db_session.flush()

        identity = IdentityORM(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind="DEVICE",
            external_key=f"dev_{uuid4()}",
        )
        db_session.add(identity)
        await db_session.flush()

        score_event = ScoreEventORM(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 1000},
        )
        db_session.add(score_event)
        await db_session.flush()

        # Create run entry
        entry = RunEntryORM(
            id=uuid4(),
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=1000.0,
            created_at=now,
            updated_at=now,
        )
        db_session.add(entry)
        await db_session.flush()

        result = await db_session.execute(select(RunEntryORM).where(RunEntryORM.id == entry.id))
        saved = result.scalar_one()

        assert saved.board_id == board_id
        assert saved.identity_id == identity_id
        assert saved.score_event_id == score_event_id
        assert saved.primary_value == 1000.0

    async def test_run_entry_cascade_delete_with_board(self, db_session) -> None:
        """Deleting a board cascades to run entries."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        identity_id = uuid4()
        score_event_id = uuid4()
        entry_id = uuid4()
        now = datetime.now(UTC)

        account = AccountORM(id=account_id, name="Test", slug="test")
        db_session.add(account)
        await db_session.flush()

        game = GameORM(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        db_session.add(game)
        await db_session.flush()

        board = BoardORM(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            short_code="TEST02",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add(board)
        await db_session.flush()

        identity = IdentityORM(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind="DEVICE",
            external_key=f"dev_{uuid4()}",
        )
        db_session.add(identity)
        await db_session.flush()

        score_event = ScoreEventORM(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 500},
        )
        db_session.add(score_event)
        await db_session.flush()

        entry = RunEntryORM(
            id=entry_id,
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=500.0,
            created_at=now,
            updated_at=now,
        )
        db_session.add(entry)
        await db_session.flush()

        # Delete board
        await db_session.delete(board)
        await db_session.flush()

        # Run entry should be deleted
        result = await db_session.execute(select(RunEntryORM).where(RunEntryORM.id == entry_id))
        assert result.scalar_one_or_none() is None

    async def test_run_entry_unique_constraint_board_score_event(self, db_session) -> None:
        """Cannot create duplicate run entries for same board and score event."""
        account_id = uuid4()
        game_id = uuid4()
        board_id = uuid4()
        identity_id = uuid4()
        score_event_id = uuid4()
        now = datetime.now(UTC)

        account = AccountORM(id=account_id, name="Test", slug="test")
        db_session.add(account)
        await db_session.flush()

        game = GameORM(id=game_id, account_id=account_id, name="Test Game", slug="test-game")
        db_session.add(game)
        await db_session.flush()

        board = BoardORM(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            short_code="TEST03",
            is_active=True,
            sort_direction="DESCENDING",
        )
        db_session.add(board)
        await db_session.flush()

        identity = IdentityORM(
            id=identity_id,
            account_id=account_id,
            game_id=game_id,
            kind="DEVICE",
            external_key=f"dev_{uuid4()}",
        )
        db_session.add(identity)
        await db_session.flush()

        score_event = ScoreEventORM(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
        )
        db_session.add(score_event)
        await db_session.flush()

        # First entry
        entry1 = RunEntryORM(
            id=uuid4(),
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=100.0,
            created_at=now,
            updated_at=now,
        )
        db_session.add(entry1)
        await db_session.flush()

        # Second entry with same board_id and score_event_id should fail
        entry2 = RunEntryORM(
            id=uuid4(),
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=200.0,
            created_at=now,
            updated_at=now,
        )
        db_session.add(entry2)

        with pytest.raises(IntegrityError):
            await db_session.flush()
