"""Score event service for managing immutable score events."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, BoardID, GameID, IdentityID, ScoreEventID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.repositories import ScoreEventRepository


class ScoreEventService:
    """Service for managing score events.

    Score events are immutable (append-only) facts about score submissions.
    This service only provides create, get, and list operations.
    No update or delete operations are available.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.repository = ScoreEventRepository(session)

    async def create_score_event(
        self,
        account_id: AccountID,
        game_id: GameID,
        board_id: BoardID,
        identity_id: IdentityID,
        event_payload: dict[str, Any],
        is_test: bool = False,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> ScoreEvent:
        """Create a new score event.

        Args:
            account_id: Account that owns this event
            game_id: Game this event belongs to
            board_id: Board this event was submitted to
            identity_id: Identity that submitted this score
            event_payload: Board-type-specific payload (value or delta)
            is_test: Whether this is a test submission
            timezone: Timezone from GeoIP lookup
            country: Country code from GeoIP lookup
            city: City name from GeoIP lookup

        Returns:
            Created ScoreEvent entity
        """
        event = ScoreEvent(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload=event_payload,
            is_test=is_test,
            timezone=timezone,
            country=country,
            city=city,
        )
        return await self.repository.create(event)

    async def get_score_event(self, event_id: ScoreEventID) -> ScoreEvent | None:
        """Get a score event by ID.

        Args:
            event_id: Score event ID

        Returns:
            ScoreEvent if found, None otherwise
        """
        return await self.repository.get_by_id(event_id)

    async def get_by_id_or_raise(self, event_id: ScoreEventID) -> ScoreEvent:
        """Get a score event by ID, raising if not found.

        Args:
            event_id: Score event ID

        Returns:
            ScoreEvent entity

        Raises:
            EntityNotFoundError: If event not found
        """
        event = await self.get_score_event(event_id)
        if event is None:
            raise EntityNotFoundError("ScoreEvent", str(event_id))
        return event

    async def list_score_events(
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        is_test: bool | None = None,
        limit: int = 50,
    ) -> PaginatedResult[ScoreEvent]:
        """List score events with optional filters.

        Args:
            account_id: Optional filter by account
            board_id: Optional filter by board
            identity_id: Optional filter by identity
            is_test: Optional filter by test flag
            limit: Maximum number of results

        Returns:
            Paginated list of score events
        """
        pagination = PaginationParams(cursor=None, limit=limit, sort=None)
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            identity_id=identity_id,
            is_test=is_test,
            pagination=pagination,
        )
