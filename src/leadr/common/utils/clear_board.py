"""Board score clearing utility for LEADR.

Removes all score data from a given board, with optional filtering by
production/test mode. After partial deletion, remaining data is recomputed
to maintain integrity.

Can be run as a module:

Usage:
    uv run python -m leadr.common.utils.clear_board --board <id_or_shortcode> --account <account_id>
    uv run python -m leadr.common.utils.clear_board --board ABC12345 --account acc_xxx --mode all
    uv run python -m leadr.common.utils.clear_board --board ABC12345 --account acc_xxx --dry-run

Options:
    --board <id_or_shortcode>   Board ID (brd_xxx) or short_code (required)
    --account <account_id>      Account ID (acc_xxx) for safety validation (required)
    --mode <production|test|all>  Which scores to clear (default: production)
    --dry-run                   Show what would be deleted without deleting
"""

import argparse
import asyncio
import logging
import sys
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM  # noqa: F401 - required for ORM relationships
from leadr.auth.adapters.orm import IdentityORM  # noqa: F401 - required for ORM relationships
from leadr.boards.adapters.orm import BoardStateORM, RunEntryORM
from leadr.boards.domain.board import Board
from leadr.boards.services.board_service import BoardService
from leadr.common.database import async_session_factory
from leadr.common.domain.ids import BoardID, IdentityID
from leadr.config import settings
from leadr.games.adapters.orm import GameORM  # noqa: F401 - required for ORM relationships
from leadr.logging import setup_logging
from leadr.scores.adapters.orm import (
    ScoreEventORM,
    ScoreFlagORM,
    ScoreSubmissionMetaORM,
)
from leadr.scores.services.score_flag_service import ScoreFlagService

logger = logging.getLogger(__name__)


def _is_board_id(board_input: str) -> bool:
    """Check if the input is a board ID (starts with 'brd_')."""
    return board_input.startswith("brd_")


def _mode_to_is_test_filter(mode: str) -> bool | None:
    """Convert mode string to is_test filter value.

    Args:
        mode: One of "production", "test", or "all"

    Returns:
        False for production, True for test, None for all
    """
    if mode == "production":
        return False
    elif mode == "test":
        return True
    else:  # all
        return None


async def resolve_board(
    session: AsyncSession,
    board_input: str,
    account_id: str,
) -> Board:
    """Resolve board from ID or short_code and validate account ownership.

    Args:
        session: Database session
        board_input: Board ID (brd_xxx) or short_code
        account_id: Account ID (acc_xxx) for validation

    Returns:
        The resolved Board

    Raises:
        ValueError: If board not found or account mismatch
    """
    board_service = BoardService(session)

    if _is_board_id(board_input):
        # Extract UUID from prefixed ID
        uuid_str = board_input[4:]  # Remove 'brd_' prefix
        board_id = BoardID(UUID(uuid_str))
        board = await board_service.get_board(board_id)
    else:
        board = await board_service.get_board_by_short_code(board_input)

    if board is None:
        raise ValueError(f"Board not found: {board_input}")

    # Validate account ownership
    expected_account_uuid = UUID(account_id.replace("acc_", ""))
    if board.account_id.uuid != expected_account_uuid:
        raise ValueError(
            f"Board {board_input} does not belong to account {account_id}. "
            f"Board belongs to account acc_{board.account_id.uuid}"
        )

    return board


async def count_affected_records(
    session: AsyncSession,
    board_id: BoardID,
    is_test_filter: bool | None,
) -> dict[str, int]:
    """Count records that would be affected by deletion.

    Args:
        session: Database session
        board_id: Board ID to count records for
        is_test_filter: Filter by is_test (None = all)

    Returns:
        Dictionary with counts for each record type
    """
    # Build base event filter
    event_conditions = [ScoreEventORM.board_id == board_id.uuid]
    if is_test_filter is not None:
        event_conditions.append(ScoreEventORM.is_test == is_test_filter)

    # Count score events
    result = await session.execute(select(func.count()).where(*event_conditions))
    score_events = result.scalar() or 0

    # Subquery for matching event IDs
    event_ids_subquery = select(ScoreEventORM.id).where(*event_conditions)

    # Count score flags
    result = await session.execute(
        select(func.count()).where(ScoreFlagORM.score_event_id.in_(event_ids_subquery))
    )
    score_flags = result.scalar() or 0

    # Count run entries
    result = await session.execute(
        select(func.count()).where(RunEntryORM.score_event_id.in_(event_ids_subquery))
    )
    run_entries = result.scalar() or 0

    # Count board states
    state_conditions = [BoardStateORM.board_id == board_id.uuid]
    if is_test_filter is not None:
        state_conditions.append(BoardStateORM.is_test == is_test_filter)
    result = await session.execute(select(func.count()).where(*state_conditions))
    board_states = result.scalar() or 0

    # Count submission metadata
    result = await session.execute(
        select(func.count()).where(ScoreSubmissionMetaORM.score_event_id.in_(event_ids_subquery))
    )
    submission_meta = result.scalar() or 0

    # Count affected identities
    result = await session.execute(
        select(func.count(ScoreEventORM.identity_id.distinct())).where(*event_conditions)
    )
    affected_identities = result.scalar() or 0

    return {
        "score_events": score_events,
        "score_flags": score_flags,
        "run_entries": run_entries,
        "board_states": board_states,
        "submission_meta": submission_meta,
        "affected_identities": affected_identities,
    }


async def get_affected_identity_ids(
    session: AsyncSession,
    board_id: BoardID,
    is_test_filter: bool | None,
) -> set[IdentityID]:
    """Get unique identity IDs affected by the deletion.

    Args:
        session: Database session
        board_id: Board ID
        is_test_filter: Filter by is_test (None = all)

    Returns:
        Set of affected IdentityIDs
    """
    event_conditions = [ScoreEventORM.board_id == board_id.uuid]
    if is_test_filter is not None:
        event_conditions.append(ScoreEventORM.is_test == is_test_filter)

    result = await session.execute(
        select(ScoreEventORM.identity_id.distinct()).where(*event_conditions)
    )
    raw_ids = result.scalars().all()
    return {IdentityID(uid) for uid in raw_ids}


async def delete_records(
    session: AsyncSession,
    board_id: BoardID,
    is_test_filter: bool | None,
) -> dict[str, int]:
    """Delete all score-related records for a board.

    Deletes in FK order to respect foreign key constraints:
    1. ScoreFlags
    2. RunEntries
    3. ScoreSubmissionMeta
    4. BoardStates
    5. ScoreEvents

    Args:
        session: Database session
        board_id: Board ID to delete records for
        is_test_filter: Filter by is_test (None = all)

    Returns:
        Dictionary with counts of deleted records
    """
    # Build base event filter
    event_conditions = [ScoreEventORM.board_id == board_id.uuid]
    if is_test_filter is not None:
        event_conditions.append(ScoreEventORM.is_test == is_test_filter)

    # Subquery for matching event IDs
    event_ids_subquery = select(ScoreEventORM.id).where(*event_conditions)

    counts: dict[str, int] = {}

    # 1. Delete ScoreFlags
    result = cast(
        CursorResult[Any],
        await session.execute(
            delete(ScoreFlagORM).where(ScoreFlagORM.score_event_id.in_(event_ids_subquery))
        ),
    )
    counts["score_flags"] = result.rowcount

    # 2. Delete RunEntries
    result = cast(
        CursorResult[Any],
        await session.execute(
            delete(RunEntryORM).where(RunEntryORM.score_event_id.in_(event_ids_subquery))
        ),
    )
    counts["run_entries"] = result.rowcount

    # 3. Delete ScoreSubmissionMeta
    result = cast(
        CursorResult[Any],
        await session.execute(
            delete(ScoreSubmissionMetaORM).where(
                ScoreSubmissionMetaORM.score_event_id.in_(event_ids_subquery)
            )
        ),
    )
    counts["submission_meta"] = result.rowcount

    # 4. Delete BoardStates
    state_conditions = [BoardStateORM.board_id == board_id.uuid]
    if is_test_filter is not None:
        state_conditions.append(BoardStateORM.is_test == is_test_filter)
    result = cast(
        CursorResult[Any],
        await session.execute(delete(BoardStateORM).where(*state_conditions)),
    )
    counts["board_states"] = result.rowcount

    # 5. Delete ScoreEvents (last, as others have FK to it)
    result = cast(
        CursorResult[Any],
        await session.execute(delete(ScoreEventORM).where(*event_conditions)),
    )
    counts["score_events"] = result.rowcount

    return counts


async def clear_board(
    board_input: str,
    account_id: str,
    mode: str = "production",
    dry_run: bool = False,
) -> dict[str, int]:
    """Clear all scores from a board.

    Args:
        board_input: Board ID (brd_xxx) or short_code
        account_id: Account ID (acc_xxx) for safety validation
        mode: Which scores to clear - "production", "test", or "all"
        dry_run: If True, only count and report without deleting

    Returns:
        Dictionary with counts of affected/deleted records

    Raises:
        ValueError: If board not found or account mismatch
    """
    is_test_filter = _mode_to_is_test_filter(mode)

    async with async_session_factory() as session:
        # Resolve and validate board
        board = await resolve_board(session, board_input, account_id)
        logger.info("Board: %s (%s)", board.name, board.id)
        logger.info("Mode: %s", mode)

        # Count affected records
        counts = await count_affected_records(session, board.id, is_test_filter)
        logger.info("Affected records:")
        logger.info("  Score events: %d", counts["score_events"])
        logger.info("  Score flags: %d", counts["score_flags"])
        logger.info("  Run entries: %d", counts["run_entries"])
        logger.info("  Board states: %d", counts["board_states"])
        logger.info("  Submission meta: %d", counts["submission_meta"])
        logger.info("  Affected identities: %d", counts["affected_identities"])

        if dry_run:
            logger.info("DRY RUN - no records deleted")
            return counts

        # Get affected identity IDs before deletion (for recomputation)
        affected_identity_ids = await get_affected_identity_ids(session, board.id, is_test_filter)

        # Delete records
        delete_counts = await delete_records(session, board.id, is_test_filter)
        logger.info("Deleted records:")
        logger.info("  Score events: %d", delete_counts["score_events"])
        logger.info("  Score flags: %d", delete_counts["score_flags"])
        logger.info("  Run entries: %d", delete_counts["run_entries"])
        logger.info("  Board states: %d", delete_counts["board_states"])
        logger.info("  Submission meta: %d", delete_counts["submission_meta"])

        # Recompute remaining state if partial deletion (not 'all' mode)
        if mode != "all" and affected_identity_ids:
            logger.info("Recomputing state for %d identities...", len(affected_identity_ids))
            flag_service = ScoreFlagService(session)
            recomputed = await flag_service.recompute_state_for_identities(
                board, affected_identity_ids
            )
            logger.info("Recomputed state for %d identities", recomputed)

        # Commit transaction
        await session.commit()
        logger.info("Board clearing completed successfully")

        return delete_counts


if __name__ == "__main__":
    setup_logging(
        log_level="DEBUG" if settings.DEBUG else "INFO",
        json_format=settings.LOG_JSON,
        log_to_file=settings.LOG_TO_FILE,
        log_dir=settings.LOG_DIR,
        app_name=settings.APP,
        env=settings.ENV,
    )

    parser = argparse.ArgumentParser(description="Clear all scores from a LEADR board")
    parser.add_argument(
        "--board",
        required=True,
        help="Board ID (brd_xxx) or short_code",
    )
    parser.add_argument(
        "--account",
        required=True,
        help="Account ID (acc_xxx) - required for safety validation",
    )
    parser.add_argument(
        "--mode",
        choices=["production", "test", "all"],
        default="production",
        help="Which scores to clear (default: production)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    try:
        asyncio.run(
            clear_board(
                board_input=args.board,
                account_id=args.account,
                mode=args.mode,
                dry_run=args.dry_run,
            )
        )
    except Exception as e:
        logger.exception("Board clearing failed: %s", str(e))
        sys.exit(1)
