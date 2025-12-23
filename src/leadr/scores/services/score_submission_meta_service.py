"""Service for score submission metadata management."""

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, ScoreSubmissionMetaID
from leadr.common.domain.pagination_result import PaginatedResult
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
        account_id: AccountID | None,
        board_id: BoardID | None = None,
        device_id: DeviceID | None = None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[ScoreSubmissionMeta]:
        """List score submission metadata for an account with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all metadata
                (superadmin use case).
            board_id: Optional board ID to filter by
            device_id: Optional device ID to filter by
            pagination: Pagination parameters (required)

        Returns:
            PaginatedResult containing submission metadata matching the filter criteria

        Example:
            >>> metas = await service.list_submission_meta(
            ...     account_id=account.id,
            ...     board_id=board.id,
            ...     pagination=PaginationParams(cursor=None, limit=100, sort=None),
            ... )
        """
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            device_id=device_id,
            pagination=pagination,
        )

    async def get_submission_meta(
        self, meta_id: ScoreSubmissionMetaID
    ) -> ScoreSubmissionMeta | None:
        """Get submission metadata by its ID.

        Args:
            meta_id: The ID of the submission metadata to retrieve

        Returns:
            The submission metadata if found, None otherwise

        Example:
            >>> meta = await service.get_submission_meta(meta_id)
        """
        return await self.get_by_id(meta_id)
