"""Board ratio config service for managing ratio board configurations."""

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    TieBreaker,
    ZeroDenominatorPolicy,
)
from leadr.boards.services.repositories import BoardRatioConfigRepository
from leadr.common.domain.ids import BoardID, BoardRatioConfigID
from leadr.common.services import BaseService


class BoardRatioConfigService(BaseService[BoardRatioConfig, BoardRatioConfigRepository]):
    """Service for managing board ratio configurations."""

    def _create_repository(self, session: AsyncSession) -> BoardRatioConfigRepository:
        """Create the repository instance.

        Args:
            session: SQLAlchemy async session.

        Returns:
            BoardRatioConfigRepository instance.
        """
        return BoardRatioConfigRepository(session)

    def _get_entity_name(self) -> str:
        """Get the entity name for error messages.

        Returns:
            String name of the entity.
        """
        return "BoardRatioConfig"

    async def create_ratio_config(
        self,
        board_id: BoardID,
        numerator_board_id: BoardID,
        denominator_board_id: BoardID,
        zero_denominator_policy: ZeroDenominatorPolicy = ZeroDenominatorPolicy.NULL,
        min_denominator: float = 0,
        min_numerator: float = 0,
        scale: int = 1_000_000,
        display: RatioDisplay = RatioDisplay.RAW,
        decimals: int = 2,
        tie_breaker: TieBreaker = TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC,
    ) -> BoardRatioConfig:
        """Create a new ratio config for a board.

        Args:
            board_id: ID of the ratio board.
            numerator_board_id: ID of the numerator board.
            denominator_board_id: ID of the denominator board.
            zero_denominator_policy: How to handle zero denominators.
            min_denominator: Minimum denominator for ranking eligibility.
            min_numerator: Minimum numerator for ranking eligibility.
            scale: Scaling factor for ratio storage.
            display: Display format for ratio values.
            decimals: Number of decimal places for display.
            tie_breaker: Strategy for breaking ties.

        Returns:
            Created BoardRatioConfig entity.
        """
        config = BoardRatioConfig(
            board_id=board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
            zero_denominator_policy=zero_denominator_policy,
            min_denominator=min_denominator,
            min_numerator=min_numerator,
            scale=scale,
            display=display,
            decimals=decimals,
            tie_breaker=tie_breaker,
        )
        return await self.repository.create(config)

    async def get_ratio_config(
        self, config_id: BoardRatioConfigID
    ) -> BoardRatioConfig | None:
        """Get a ratio config by ID.

        Args:
            config_id: The ratio config ID.

        Returns:
            BoardRatioConfig if found, None otherwise.
        """
        return await self.repository.get_by_id(config_id)

    async def get_by_board_id(self, board_id: BoardID) -> BoardRatioConfig | None:
        """Get the ratio config for a specific board.

        Args:
            board_id: The ratio board ID.

        Returns:
            BoardRatioConfig if found, None otherwise.
        """
        return await self.repository.get_by_board_id(board_id)

    async def update_ratio_config(
        self,
        config_id: BoardRatioConfigID,
        zero_denominator_policy: ZeroDenominatorPolicy | None = None,
        min_denominator: float | None = None,
        min_numerator: float | None = None,
        scale: int | None = None,
        display: RatioDisplay | None = None,
        decimals: int | None = None,
        tie_breaker: TieBreaker | None = None,
    ) -> BoardRatioConfig:
        """Update a ratio config.

        Args:
            config_id: The ratio config ID.
            zero_denominator_policy: New zero denominator policy.
            min_denominator: New minimum denominator.
            min_numerator: New minimum numerator.
            scale: New scale.
            display: New display format.
            decimals: New decimal places.
            tie_breaker: New tie breaker strategy.

        Returns:
            Updated BoardRatioConfig entity.

        Raises:
            EntityNotFoundError: If config not found.
        """
        config = await self.get_by_id_or_raise(config_id)

        if zero_denominator_policy is not None:
            config.zero_denominator_policy = zero_denominator_policy
        if min_denominator is not None:
            config.min_denominator = min_denominator
        if min_numerator is not None:
            config.min_numerator = min_numerator
        if scale is not None:
            config.scale = scale
        if display is not None:
            config.display = display
        if decimals is not None:
            config.decimals = decimals
        if tie_breaker is not None:
            config.tie_breaker = tie_breaker

        return await self.repository.update(config)
