"""Service for score submission metadata management."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.services import BaseService
from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository


class ScoreSubmissionMetaService(BaseService[ScoreSubmissionMeta, ScoreSubmissionMetaRepository]):
    """Service for managing score submission metadata.

    Provides read-only access to submission metadata for debugging and analysis.
    """

    def _create_repository(self, session: AsyncSession) -> ScoreSubmissionMetaRepository:
        """Create repository instance."""
        return ScoreSubmissionMetaRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "ScoreSubmissionMeta"

    async def list_submission_meta(
        self,
        account_id: UUID,
        board_id: UUID | None = None,
        device_id: UUID | None = None,
    ) -> list[ScoreSubmissionMeta]:
        """List score submission metadata for an account with optional filters.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            board_id: Optional board ID to filter by
            device_id: Optional device ID to filter by

        Returns:
            List of submission metadata matching the filter criteria

        Example:
            >>> metas = await service.list_submission_meta(
            ...     account_id=account.id,
            ...     board_id=board.id,
            ... )
        """
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            device_id=device_id,
        )

    async def get_submission_meta(self, meta_id: UUID) -> ScoreSubmissionMeta | None:
        """Get submission metadata by its ID.

        Args:
            meta_id: The ID of the submission metadata to retrieve

        Returns:
            The submission metadata if found, None otherwise

        Example:
            >>> meta = await service.get_submission_meta(meta_id)
        """
        return await self.get_by_id(meta_id)
