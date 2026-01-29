"""Score repository services."""

from typing import Any

from sqlalchemy import select

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import ImmutableBaseRepository
from leadr.scores.adapters.orm import ScoreEventORM
from leadr.scores.domain.score_event import ScoreEvent


class ScoreEventRepository(ImmutableBaseRepository[ScoreEvent, ScoreEventORM]):
    """Repository for managing score event persistence.

    Score events are immutable (append-only) so this repository
    does not support update or delete operations.
    """

    async def filter(
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        is_test: bool | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[ScoreEvent]:
        """Filter score events based on criteria with pagination.

        Args:
            account_id: Optional account ID filter
            board_id: Optional board ID filter
            identity_id: Optional identity ID filter
            is_test: Optional filter for test events
            pagination: Required pagination parameters

        Returns:
            PaginatedResult containing score events
        """
        query = select(ScoreEventORM)

        if account_id is not None:
            query = query.where(ScoreEventORM.account_id == self._extract_uuid(account_id))
        if board_id is not None:
            query = query.where(ScoreEventORM.board_id == self._extract_uuid(board_id))
        if identity_id is not None:
            query = query.where(ScoreEventORM.identity_id == self._extract_uuid(identity_id))
        if is_test is not None:
            query = query.where(ScoreEventORM.is_test == is_test)

        return await self._execute_paginated_query(
            query=query,
            sort_fields=pagination.sort_spec,
            cursor=pagination.decode_cursor() if pagination.has_cursor() else None,
            limit=pagination.limit,
        )

    def _to_domain(self, orm: ScoreEventORM) -> ScoreEvent:
        """Convert ORM model to domain entity.

        Args:
            orm: ScoreEventORM model instance

        Returns:
            ScoreEvent domain entity
        """
        return ScoreEvent(
            id=ScoreEventID(orm.id),
            account_id=AccountID(orm.account_id),
            game_id=GameID(orm.game_id),
            board_id=BoardID(orm.board_id),
            identity_id=IdentityID(orm.identity_id),
            event_payload=orm.event_payload,
            is_test=orm.is_test,
            timezone=orm.timezone,
            country=orm.country,
            city=orm.city,
            created_at=orm.created_at,
        )

    def _to_orm(self, entity: ScoreEvent) -> ScoreEventORM:
        """Convert domain entity to ORM model."""
        return ScoreEventORM(
            id=entity.id.uuid,
            account_id=entity.account_id.uuid,
            game_id=entity.game_id.uuid,
            board_id=entity.board_id.uuid,
            identity_id=entity.identity_id.uuid,
            event_payload=entity.event_payload,
            is_test=entity.is_test,
            timezone=entity.timezone,
            country=entity.country,
            city=entity.city,
            created_at=entity.created_at,
        )

    def _get_orm_class(self) -> type[ScoreEventORM]:
        """Get the ORM model class."""
        return ScoreEventORM
