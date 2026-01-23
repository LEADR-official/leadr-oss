"""Board state service for managing materialized ranking state."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board_state import BoardState
from leadr.boards.services.repositories import BoardStateRepository
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
    ) -> BoardState:
        """Create a new board state.

        Args:
            board_id: Board this state belongs to
            identity_id: Identity this state is for
            primary_value: Rankable value (None = not rankable)
            aux: Board-type-specific auxiliary data

        Returns:
            Created BoardState entity
        """
        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=primary_value,
            aux=aux,
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
    ) -> BoardState:
        """Create or update a board state.

        If a state already exists for the board/identity combination, it is updated.
        Otherwise, a new state is created.

        Args:
            board_id: Board this state belongs to
            identity_id: Identity this state is for
            primary_value: Rankable value (None = not rankable)
            aux: Board-type-specific auxiliary data

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
            )

        # Update existing state
        existing.primary_value = primary_value
        existing.aux = aux
        return await self.repository.update(existing)

    async def list_board_states(
        self,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        limit: int = 50,
    ) -> PaginatedResult[BoardState]:
        """List board states with optional filters.

        Args:
            board_id: Optional filter by board
            identity_id: Optional filter by identity
            limit: Maximum number of results

        Returns:
            Paginated list of board states
        """
        pagination = PaginationParams(cursor=None, limit=limit, sort=None)
        return await self.repository.filter(
            board_id=board_id,
            identity_id=identity_id,
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
