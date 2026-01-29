"""Run entry service for managing run entries."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.repositories import RunEntryRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, IdentityID, RunEntryID, ScoreEventID
from leadr.common.domain.pagination_result import PaginatedResult


class RunEntryService:
    """Service for managing run entries.

    Run entries represent individual scored submissions for RUN_RUNS boards
    where every submission is ranked.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the run entry service.

        Args:
            session: Database session for persistence operations.
        """
        self.session = session
        self.repository = RunEntryRepository(session)

    async def create_run_entry(
        self,
        *,
        board_id: BoardID,
        identity_id: IdentityID,
        score_event_id: ScoreEventID,
        primary_value: float,
        player_name: str = "",
        is_test: bool = False,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
        value_display: str | None = None,
        metadata: Any | None = None,
    ) -> RunEntry:
        """Create a new run entry.

        Args:
            board_id: The board this entry belongs to.
            identity_id: The identity that submitted this entry.
            score_event_id: The score event that created this entry.
            primary_value: The rankable value for this submission.
            player_name: Display name at submission time.
            is_test: Whether this is a test submission.
            timezone: Timezone from GeoIP.
            country: Country code from GeoIP.
            city: City name from GeoIP.
            value_display: Formatted display string.
            metadata: Game-specific JSON metadata.

        Returns:
            The created run entry.
        """
        entry = RunEntry(
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=primary_value,
            player_name=player_name,
            is_test=is_test,
            timezone=timezone,
            country=country,
            city=city,
            value_display=value_display,
            metadata=metadata,
        )
        return await self.repository.create(entry)

    async def get_run_entry(self, entry_id: RunEntryID) -> RunEntry | None:
        """Get a run entry by ID.

        Args:
            entry_id: The run entry ID to look up.

        Returns:
            The run entry if found, None otherwise.
        """
        return await self.repository.get_by_id(entry_id)

    async def get_by_id_or_raise(self, entry_id: RunEntryID) -> RunEntry:
        """Get a run entry by ID or raise if not found.

        Args:
            entry_id: The run entry ID to look up.

        Returns:
            The run entry.

        Raises:
            EntityNotFoundError: If the run entry does not exist.
        """
        entry = await self.repository.get_by_id(entry_id)
        if entry is None:
            raise EntityNotFoundError(entity_type="RunEntry", entity_id=str(entry_id))
        return entry

    async def get_by_board_and_score_event(
        self,
        board_id: BoardID,
        score_event_id: ScoreEventID,
    ) -> RunEntry | None:
        """Get a run entry by board and score event.

        Args:
            board_id: The board ID to search for.
            score_event_id: The score event ID to search for.

        Returns:
            The run entry if found, None otherwise.
        """
        return await self.repository.get_by_board_and_score_event(board_id, score_event_id)

    async def list_run_entries(
        self,
        *,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        is_test: bool | None = None,
        pagination: PaginationParams | None = None,
        around_entry: RunEntry | None = None,
        around_value: float | None = None,
    ) -> PaginatedResult[RunEntry]:
        """List run entries with optional filtering.

        Args:
            board_id: Optional board ID to filter by.
            identity_id: Optional identity ID to filter by.
            is_test: Optional filter for test entries (True=test only, False=prod only, None=all).
            pagination: Optional pagination parameters.
            around_entry: Optional target entry to center results around.
            around_value: Optional value to center results around (creates placeholder).

        Returns:
            Paginated list of run entries.
        """
        if pagination is None:
            pagination = PaginationParams(limit=50, cursor=None, sort=None)

        # If around_value is provided, use around value query with placeholder
        if around_value is not None and board_id is not None:
            return await self.repository.execute_around_value_query(
                board_id=board_id,
                target_value=around_value,
                sort_fields=pagination.sort_spec,
                limit=pagination.limit,
                is_test=is_test,
            )

        # If around_entry is provided, use around query
        if around_entry is not None and board_id is not None:
            return await self.repository.execute_around_query(
                board_id=board_id,
                target_entry=around_entry,
                sort_fields=pagination.sort_spec,
                limit=pagination.limit,
                is_test=is_test,
            )

        return await self.repository.filter(
            board_id=board_id,
            identity_id=identity_id,
            is_test=is_test,
            pagination=pagination,
        )

    async def soft_delete(self, entry_id: RunEntryID) -> RunEntry:
        """Soft delete a run entry.

        Args:
            entry_id: The run entry ID to delete.

        Returns:
            The deleted run entry.

        Raises:
            EntityNotFoundError: If the run entry does not exist.
        """
        entry = await self.repository.get_by_id(entry_id)
        if entry is None:
            raise EntityNotFoundError(entity_type="RunEntry", entity_id=str(entry_id))
        entry.soft_delete()
        return await self.repository.update(entry)
