"""Board state service for managing materialized ranking state."""

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.adapters.orm import BoardRatioConfigORM
from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    ZeroDenominatorPolicy,
)
from leadr.boards.domain.board_state import BoardState
from leadr.boards.services.repositories import (
    BoardRatioConfigRepository,
    BoardStateRepository,
)
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, BoardStateID, IdentityID
from leadr.common.domain.pagination_result import PaginatedResult


class BoardStateService:
    """Service for managing board states.

    Board states represent the materialized ranking state for identities on boards.
    Each identity has at most one state per board. States are updated when new
    score events are processed.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.repository = BoardStateRepository(session)

    async def create_board_state(
        self,
        board_id: BoardID,
        identity_id: IdentityID,
        primary_value: float | None = None,
        aux: dict[str, Any] | None = None,
        *,
        player_name: str = "",
        is_test: bool = False,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
        value_display: str | None = None,
        metadata: Any | None = None,
    ) -> BoardState:
        """Create a new board state.

        Args:
            board_id: Board this state belongs to
            identity_id: Identity this state is for
            primary_value: Rankable value (None = not rankable)
            aux: Board-type-specific auxiliary data
            player_name: Display name at submission time
            is_test: Whether this is a test submission
            timezone: Timezone from GeoIP
            country: Country code from GeoIP
            city: City name from GeoIP
            value_display: Formatted display string
            metadata: Game-specific JSON metadata

        Returns:
            Created BoardState entity
        """
        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=primary_value,
            aux=aux,
            player_name=player_name,
            is_test=is_test,
            timezone=timezone,
            country=country,
            city=city,
            value_display=value_display,
            metadata=metadata,
        )
        return await self.repository.create(state)

    async def get_board_state(self, state_id: BoardStateID) -> BoardState | None:
        """Get a board state by ID.

        Args:
            state_id: Board state ID

        Returns:
            BoardState if found, None otherwise
        """
        return await self.repository.get_by_id(state_id)

    async def get_by_id_or_raise(self, state_id: BoardStateID) -> BoardState:
        """Get a board state by ID, raising if not found.

        Args:
            state_id: Board state ID

        Returns:
            BoardState entity

        Raises:
            EntityNotFoundError: If state not found
        """
        state = await self.get_board_state(state_id)
        if state is None:
            raise EntityNotFoundError("BoardState", str(state_id))
        return state

    async def get_by_board_and_identity(
        self,
        board_id: BoardID,
        identity_id: IdentityID,
    ) -> BoardState | None:
        """Get a board state by board and identity.

        Args:
            board_id: Board ID
            identity_id: Identity ID

        Returns:
            BoardState if found, None otherwise
        """
        return await self.repository.get_by_board_and_identity(board_id, identity_id)

    async def upsert_board_state(
        self,
        board_id: BoardID,
        identity_id: IdentityID,
        primary_value: float | None = None,
        aux: dict[str, Any] | None = None,
        *,
        player_name: str = "",
        is_test: bool = False,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
        value_display: str | None = None,
        metadata: Any | None = None,
    ) -> BoardState:
        """Create or update a board state.

        If a state already exists for the board/identity combination, it is updated.
        Otherwise, a new state is created.

        Args:
            board_id: Board this state belongs to
            identity_id: Identity this state is for
            primary_value: Rankable value (None = not rankable)
            aux: Board-type-specific auxiliary data
            player_name: Display name at submission time
            is_test: Whether this is a test submission
            timezone: Timezone from GeoIP
            country: Country code from GeoIP
            city: City name from GeoIP
            value_display: Formatted display string
            metadata: Game-specific JSON metadata

        Returns:
            Created or updated BoardState entity
        """
        existing = await self.repository.get_by_board_and_identity(board_id, identity_id)

        if existing is None:
            # Create new state
            return await self.create_board_state(
                board_id=board_id,
                identity_id=identity_id,
                primary_value=primary_value,
                aux=aux,
                player_name=player_name,
                is_test=is_test,
                timezone=timezone,
                country=country,
                city=city,
                value_display=value_display,
                metadata=metadata,
            )

        # Update existing state
        existing.primary_value = primary_value
        existing.aux = aux
        existing.player_name = player_name
        existing.is_test = is_test
        existing.timezone = timezone
        existing.country = country
        existing.city = city
        existing.value_display = value_display
        existing.metadata = metadata
        return await self.repository.update(existing)

    async def list_board_states(
        self,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        is_test: bool | None = None,
        pagination: PaginationParams | None = None,
        around_state: BoardState | None = None,
        around_value: float | None = None,
    ) -> PaginatedResult[BoardState]:
        """List board states with optional filters.

        Args:
            board_id: Optional filter by board
            identity_id: Optional filter by identity
            is_test: Optional filter for test entries (True=test only, False=prod only, None=all)
            pagination: Optional pagination parameters
            around_state: Optional target state to center results around
            around_value: Optional value to center results around (creates placeholder)

        Returns:
            Paginated list of board states
        """
        if pagination is None:
            pagination = PaginationParams(cursor=None, limit=50, sort=None)

        # If around_value is provided, use around value query with placeholder
        if around_value is not None and board_id is not None:
            return await self.repository.execute_around_value_query(
                board_id=board_id,
                target_value=around_value,
                sort_fields=pagination.sort_spec,
                limit=pagination.limit,
                is_test=is_test,
            )

        # If around_state is provided, use around query
        if around_state is not None and board_id is not None:
            return await self.repository.execute_around_query(
                board_id=board_id,
                target_state=around_state,
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

    async def soft_delete(self, state_id: BoardStateID) -> BoardState:
        """Soft delete a board state.

        Args:
            state_id: Board state ID

        Returns:
            The soft-deleted BoardState entity

        Raises:
            EntityNotFoundError: If state not found
        """
        state = await self.get_by_id_or_raise(state_id)
        state.soft_delete()
        return await self.repository.update(state)

    # -------------------------------------------------------------------------
    # RATIO board recomputation
    # -------------------------------------------------------------------------

    async def find_dependent_ratio_boards(
        self,
        board_id: BoardID,
    ) -> list[BoardRatioConfig]:
        """Find RATIO boards where this board is numerator or denominator.

        Args:
            board_id: The board ID to check for dependencies.

        Returns:
            List of BoardRatioConfig entities that depend on this board.
        """
        query = select(BoardRatioConfigORM).where(
            BoardRatioConfigORM.deleted_at.is_(None),
            or_(
                BoardRatioConfigORM.numerator_board_id == board_id.uuid,
                BoardRatioConfigORM.denominator_board_id == board_id.uuid,
            ),
        )

        result = await self.session.execute(query)
        orms = result.scalars().all()

        repo = BoardRatioConfigRepository(self.session)
        return [repo._to_domain(orm) for orm in orms]

    async def recompute_ratio_for_identity(
        self,
        ratio_config: BoardRatioConfig,
        identity_id: IdentityID,
    ) -> BoardState | None:
        """Recalculate ratio value and upsert board state.

        Fetches the numerator and denominator values from the source boards,
        calculates the ratio, and creates/updates the ratio board state.

        Args:
            ratio_config: The ratio configuration specifying source boards.
            identity_id: The identity to recompute the ratio for.

        Returns:
            The created/updated BoardState, or None if source data is missing.
        """
        # Get numerator value
        numerator_state = await self.repository.get_by_board_and_identity(
            ratio_config.numerator_board_id,
            identity_id,
        )

        # Get denominator value
        denominator_state = await self.repository.get_by_board_and_identity(
            ratio_config.denominator_board_id,
            identity_id,
        )

        # If either source is missing, we can't compute a ratio
        if numerator_state is None or denominator_state is None:
            return None

        numerator_value = numerator_state.primary_value or 0.0
        denominator_value = denominator_state.primary_value or 0.0

        # Calculate the ratio value
        primary_value = self._calculate_ratio_value(
            numerator_value=numerator_value,
            denominator_value=denominator_value,
            config=ratio_config,
        )

        # Build aux data
        aux = {
            "numerator_value": numerator_value,
            "denominator_value": denominator_value,
        }

        # Determine test status (inherit from source states - both should match)
        is_test = numerator_state.is_test

        # Get existing ratio state
        existing_state = await self.repository.get_by_board_and_identity(
            ratio_config.board_id,
            identity_id,
        )

        if existing_state is None:
            # Create new state
            state = BoardState(
                board_id=ratio_config.board_id,
                identity_id=identity_id,
                primary_value=primary_value,
                aux=aux,
                is_test=is_test,
                # Inherit player name from numerator state
                player_name=numerator_state.player_name,
                timezone=numerator_state.timezone,
                country=numerator_state.country,
                city=numerator_state.city,
            )
            return await self.repository.create(state)
        else:
            # Update existing state
            existing_state.primary_value = primary_value
            existing_state.aux = aux
            existing_state.is_test = is_test
            existing_state.player_name = numerator_state.player_name
            existing_state.timezone = numerator_state.timezone
            existing_state.country = numerator_state.country
            existing_state.city = numerator_state.city
            return await self.repository.update(existing_state)

    def _calculate_ratio_value(
        self,
        numerator_value: float,
        denominator_value: float,
        config: BoardRatioConfig,
    ) -> float | None:
        """Calculate the ratio value based on configuration.

        Args:
            numerator_value: The numerator value.
            denominator_value: The denominator value.
            config: The ratio configuration.

        Returns:
            The calculated ratio * scale, or None if not rankable.
        """
        # Check min_denominator threshold
        if denominator_value < config.min_denominator:
            return None

        # Check min_numerator threshold
        if numerator_value < config.min_numerator:
            return None

        # Handle zero denominator
        if denominator_value == 0:
            if config.zero_denominator_policy == ZeroDenominatorPolicy.NULL:
                return None
            elif config.zero_denominator_policy == ZeroDenominatorPolicy.ZERO:
                return 0.0
            elif config.zero_denominator_policy == ZeroDenominatorPolicy.INFINITY:
                # Use a very large value for "infinity"
                return float(config.scale) * 1_000_000
            else:
                return None

        # Calculate ratio with scale
        ratio = (numerator_value / denominator_value) * config.scale
        return ratio
