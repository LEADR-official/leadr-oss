"""Score flag service for managing flag operations."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.ids import AccountID, BoardID, GameID, ScoreFlagID, UserID
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
        account_id: AccountID,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        status: str | None = None,
        flag_type: str | None = None,
    ) -> list[ScoreFlag]:
        """List score flags for an account with optional filters.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            status: Optional status to filter by (PENDING, CONFIRMED_CHEAT, etc.)
            flag_type: Optional flag type to filter by (VELOCITY, DUPLICATE, etc.)

        Returns:
            List of flags matching the filter criteria

        Example:
            >>> flags = await service.list_flags(
            ...     account_id=account.id,
            ...     status="PENDING",
            ... )
        """
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            status=status,
            flag_type=flag_type,
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

    async def review_flag(
        self,
        flag_id: ScoreFlagID,
        status: ScoreFlagStatus,
        reviewer_decision: str | None = None,
        reviewer_id: UserID | None = None,
    ) -> ScoreFlag:
        """Review a flag and update its status.

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

        # Update review fields
        flag.status = status
        flag.reviewed_at = datetime.now(UTC)
        if reviewer_decision is not None:
            flag.reviewer_decision = reviewer_decision
        if reviewer_id is not None:
            flag.reviewer_id = reviewer_id

        return await self.repository.update(flag)

    async def update_flag(
        self,
        flag_id: ScoreFlagID,
        status: ScoreFlagStatus | None = None,
        reviewer_decision: str | None = None,
    ) -> ScoreFlag:
        """Update a flag's status and/or reviewer decision.

        Args:
            flag_id: The ID of the flag to update
            status: Optional new status
            reviewer_decision: Optional new reviewer decision

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

        # Update fields if provided
        if status is not None:
            flag.status = status
            flag.reviewed_at = datetime.now(UTC)

        if reviewer_decision is not None:
            flag.reviewer_decision = reviewer_decision

        return await self.repository.update(flag)
