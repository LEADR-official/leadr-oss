"""Score repository services."""

from typing import Any

from sqlalchemy import select

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository
from leadr.scores.adapters.orm import ScoreORM
from leadr.scores.domain.score import Score


class ScoreRepository(BaseRepository[Score, ScoreORM]):
    """Score repository for managing score persistence."""

    def _to_domain(self, orm: ScoreORM) -> Score:
        """Convert ORM model to domain entity."""
        return Score(
            id=ScoreID(orm.id),
            account_id=AccountID(orm.account_id),
            game_id=GameID(orm.game_id),
            board_id=BoardID(orm.board_id),
            device_id=DeviceID(orm.device_id),
            player_name=orm.player_name,
            value=orm.value,
            value_display=orm.value_display,
            timezone=orm.filter_timezone,
            country=orm.filter_country,
            city=orm.filter_city,
            metadata=orm.score_metadata,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: Score) -> ScoreORM:
        """Convert domain entity to ORM model."""
        return ScoreORM(
            id=entity.id.uuid,
            account_id=entity.account_id.uuid,
            game_id=entity.game_id.uuid,
            board_id=entity.board_id.uuid,
            device_id=entity.device_id.uuid,
            player_name=entity.player_name,
            value=entity.value,
            value_display=entity.value_display,
            filter_timezone=entity.timezone,
            filter_country=entity.country,
            filter_city=entity.city,
            score_metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[ScoreORM]:
        """Get the ORM model class."""
        return ScoreORM

    async def get_by_device_and_board(
        self,
        account_id: AccountID,
        device_id: DeviceID,
        board_id: BoardID,
    ) -> Score | None:
        """Get the active score for a specific device on a board.

        This is an optimized single-record lookup for keep_strategy logic.

        Args:
            account_id: Account ID to filter by (multi-tenant safety).
            device_id: Device ID to search for.
            board_id: Board ID to search for.

        Returns:
            The first matching Score or None if no score exists.
        """
        query = (
            select(ScoreORM)
            .where(ScoreORM.deleted_at.is_(None))
            .where(ScoreORM.account_id == self._extract_uuid(account_id))
            .where(ScoreORM.device_id == self._extract_uuid(device_id))
            .where(ScoreORM.board_id == self._extract_uuid(board_id))
            .limit(1)
        )
        result = await self.session.execute(query)
        orm = result.scalars().first()
        return self._to_domain(orm) if orm else None

    # Valid sortable fields for scores
    SORTABLE_FIELDS = {
        "id",
        "value",
        "player_name",
        "filter_timezone",
        "filter_country",
        "filter_city",
        "created_at",
        "updated_at",
    }

    async def filter(
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        device_id: DeviceID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[Score]:
        """Filter scores by account and optional criteria.

        Args:
            account_id: Optional account ID to filter by. If None, returns all scores
                (superadmin use case). Regular users should always pass account_id.
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            device_id: Optional device ID to filter by
            pagination: Pagination parameters (required)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing scores

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        # Build base query
        query = select(ScoreORM).where(ScoreORM.deleted_at.is_(None))

        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(ScoreORM.account_id == account_uuid)

        # Apply optional filters
        filters_dict = {}
        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(ScoreORM.board_id == board_uuid)
            filters_dict["board_id"] = str(board_id)

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(ScoreORM.game_id == game_uuid)
            filters_dict["game_id"] = str(game_id)

        if device_id is not None:
            device_uuid = self._extract_uuid(device_id)
            query = query.where(ScoreORM.device_id == device_uuid)
            filters_dict["device_id"] = str(device_id)

        # Validate sort fields
        for sort_field in pagination.sort_spec:
            if sort_field.name not in self.SORTABLE_FIELDS:
                raise ValueError(
                    f"Unknown sort field: {sort_field.name}. "
                    f"Valid fields: {', '.join(sorted(self.SORTABLE_FIELDS))}"
                )

        # Handle cursor if present
        cursor = None
        if pagination.has_cursor():
            cursor = pagination.decode_cursor()
            # Validate cursor state matches current query
            if cursor is not None:
                cursor.validate_state(pagination.sort_spec, filters_dict)

        # Execute paginated query
        return await self._execute_paginated_query(
            query=query,
            sort_fields=pagination.sort_spec,
            cursor=cursor,
            limit=pagination.limit,
        )
