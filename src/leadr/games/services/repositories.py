"""Game repository services."""

from typing import Any, overload

from pydantic import UUID4
from sqlalchemy import select

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, GameID, PrefixedID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository
from leadr.games.adapters.orm import GameORM
from leadr.games.domain.game import Game


class GameRepository(BaseRepository[Game, GameORM]):
    """Game repository for managing game persistence."""

    # Valid sortable fields for games
    SORTABLE_FIELDS = {
        "id",
        "name",
        "slug",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: GameORM) -> Game:
        """Convert ORM model to domain entity."""
        return Game(
            id=GameID(orm.id),
            account_id=AccountID(orm.account_id),
            name=orm.name,
            slug=orm.slug,
            steam_app_id=orm.steam_app_id,
            default_board_id=BoardID(orm.default_board_id) if orm.default_board_id else None,
            anti_cheat_enabled=orm.anti_cheat_enabled,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: Game) -> GameORM:
        """Convert domain entity to ORM model."""
        return GameORM(
            id=entity.id.uuid,
            account_id=entity.account_id.uuid,
            name=entity.name,
            slug=entity.slug,
            steam_app_id=entity.steam_app_id,
            default_board_id=entity.default_board_id.uuid if entity.default_board_id else None,
            anti_cheat_enabled=entity.anti_cheat_enabled,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[GameORM]:
        """Get the ORM model class."""
        return GameORM

    async def get_by_slug(self, slug: str) -> Game | None:
        """Get game by slug (globally unique lookup).

        Args:
            slug: The game slug to search for.

        Returns:
            Game domain entity if found, None otherwise.
        """
        query = select(GameORM).where(
            GameORM.slug == slug,
            GameORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    @overload
    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: None = None,
        **kwargs: Any,
    ) -> list[Game]: ...

    @overload
    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: PaginationParams = ...,
        **kwargs: Any,
    ) -> PaginatedResult[Game]: ...

    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: PaginationParams | None = None,
        **kwargs: Any,
    ) -> list[Game] | PaginatedResult[Game]:
        """Filter games by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            pagination: Optional pagination parameters
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of games if no pagination, PaginatedResult if pagination provided

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering games")
        account_uuid = self._extract_uuid(account_id)
        query = select(GameORM).where(
            GameORM.account_id == account_uuid,
            GameORM.deleted_at.is_(None),
        )

        # Build filters dict for cursor validation
        filters_dict = {}

        # Future: Add additional filters here as needed
        # if "name" in kwargs:
        #     query = query.where(GameORM.name == kwargs["name"])
        #     filters_dict["name"] = kwargs["name"]

        # If no pagination, return list (backward compatibility)
        if pagination is None:
            result = await self.session.execute(query)
            orms = result.scalars().all()
            return [self._to_domain(orm) for orm in orms]

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
            if cursor is not None:
                cursor.validate_state(pagination.sort_spec, filters_dict)

        # Execute paginated query
        return await self._execute_paginated_query(
            query=query,
            sort_fields=pagination.sort_spec,
            cursor=cursor,
            limit=pagination.limit,
        )
