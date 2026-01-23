"""Score flag service for managing flag operations."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, GameID, ScoreFlagID, UserID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.scores.domain.anti_cheat.enums import ScoreFlagStatus
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.services.anti_cheat_repositories import ScoreFlagRepository


class ScoreFlagService(BaseService[ScoreFlag, ScoreFlagRepository]):
    """Service for managing score flag lifecycle and operations.

    This service orchestrates flag listing, retrieval, and review operations
    by coordinating between the domain models and repository layer.
    """

    def _create_repository(self, session: AsyncSession) -> ScoreFlagRepository:
        """Create ScoreFlagRepository instance."""
        return ScoreFlagRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "ScoreFlag"

    async def list_flags(
        self,
        account_id: AccountID | None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        status: str | None = None,
        flag_type: str | None = None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[ScoreFlag]:
        """List score flags for an account with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all flags
                (superadmin use case).
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            status: Optional status to filter by (PENDING, CONFIRMED_CHEAT, etc.)
            flag_type: Optional flag type to filter by (VELOCITY, DUPLICATE, etc.)
            pagination: Pagination parameters (required)

        Returns:
            PaginatedResult containing flags matching the filter criteria

        Example:
            >>> flags = await service.list_flags(
            ...     account_id=account.id,
            ...     status="pending",
            ...     pagination=PaginationParams(cursor=None, limit=100, sort=None),
            ... )
        """
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            status=status,
            flag_type=flag_type,
            pagination=pagination,
        )

    async def get_flag(self, flag_id: ScoreFlagID) -> ScoreFlag | None:
        """Get a flag by its ID.

        Args:
            flag_id: The ID of the flag to retrieve

        Returns:
            The flag if found, None otherwise

        Example:
            >>> flag = await service.get_flag(flag_id)
        """
        return await self.get_by_id(flag_id)

    async def _sync_ranking_status(self, flag: ScoreFlag, new_flag_status: ScoreFlagStatus) -> None:
        """Sync ranking status based on flag status change.

        When a flag is reviewed, the ranking should be updated:
        - CONFIRMED_CHEAT → Remove from ranking (soft-delete run_entry or clear board_state)
        - FALSE_POSITIVE or DISMISSED → Restore to ranking if needed

        Note: This method currently does not update rankings as part of the
        event-sourcing migration. Full implementation will be added later.

        Args:
            flag: The flag being reviewed (contains score_event_id)
            new_flag_status: The new status being set on the flag
        """
        # TODO: Implement ranking update for event-sourcing architecture
        # When CONFIRMED_CHEAT:
        #   - Find BoardState or RunEntry for the flagged score_event_id
        #   - Soft-delete RunEntry or recompute BoardState
        # When FALSE_POSITIVE/DISMISSED:
        #   - Restore to ranking if it was previously removed
        _ = flag.score_event_id  # Reference to silence unused warning
        _ = new_flag_status

    async def review_flag(
        self,
        flag_id: ScoreFlagID,
        status: ScoreFlagStatus,
        reviewer_decision: str | None = None,
        reviewer_id: UserID | None = None,
    ) -> ScoreFlag:
        """Review a flag and update its status.

        Note: Ranking updates for flag status changes are not yet implemented
        in the event-sourcing architecture.

        Args:
            flag_id: The ID of the flag to review
            status: New status (CONFIRMED_CHEAT, FALSE_POSITIVE, DISMISSED)
            reviewer_decision: Optional admin notes/decision
            reviewer_id: Optional ID of the reviewing admin

        Returns:
            The updated flag

        Raises:
            EntityNotFoundError: If the flag doesn't exist

        Example:
            >>> flag = await service.review_flag(
            ...     flag_id=flag.id,
            ...     status=ScoreFlagStatus.CONFIRMED_CHEAT,
            ...     reviewer_decision="Verified cheating behavior",
            ... )
        """
        flag = await self.get_by_id_or_raise(flag_id)

        # Sync score status with flag decision
        await self._sync_ranking_status(flag, status)

        # Update review fields
        flag.status = status
        flag.reviewed_at = datetime.now(UTC)
        if reviewer_decision is not None:
            flag.reviewer_decision = reviewer_decision
        if reviewer_id is not None:
            flag.reviewer_id = reviewer_id

        return await self.repository.update(flag)

    async def update_flag(self, flag_id: ScoreFlagID, **updates: Any) -> ScoreFlag:
        """Update a flag's status and/or reviewer decision.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Note: When status is updated, reviewed_at is automatically set
        to the current time.

        Args:
            flag_id: The ID of the flag to update
            **updates: Field names and values to update

        Returns:
            The updated flag

        Raises:
            EntityNotFoundError: If the flag doesn't exist

        Example:
            >>> flag = await service.update_flag(
            ...     flag_id=flag.id,
            ...     status=ScoreFlagStatus.FALSE_POSITIVE,
            ... )
        """
        flag = await self.get_by_id_or_raise(flag_id)

        # Special handling: when status is updated, also set reviewed_at and sync score
        if "status" in updates:
            flag.reviewed_at = datetime.now(UTC)

            # Sync score status with flag decision
            new_status = updates["status"]
            if isinstance(new_status, str):
                new_status = ScoreFlagStatus(new_status)
            await self._sync_ranking_status(flag, new_status)

        for field, value in updates.items():
            setattr(flag, field, value)

        return await self.repository.update(flag)
