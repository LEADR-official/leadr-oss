"""Game repository services."""

from typing import Any

from sqlalchemy import select

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, GameID
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
            description=orm.description,
            tags=orm.tags,
            page_url=orm.page_url,
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
            description=entity.description,
            tags=entity.tags,
            page_url=entity.page_url,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[GameORM]:
        """Get the ORM model class."""
        return GameORM

    async def get_by_slug(self, slug: str, include_deleted: bool = False) -> Game | None:
        """Get game by slug (globally unique lookup).

        Args:
            slug: The game slug to search for.
            include_deleted: If True, include soft-deleted games. Use this for
                uniqueness checks since the slug constraint is global.

        Returns:
            Game domain entity if found, None otherwise.
        """
        query = select(GameORM).where(GameORM.slug == slug)

        if not include_deleted:
            query = query.where(GameORM.deleted_at.is_(None))

        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(
        self,
        account_id: AccountID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[Game]:
        """Filter games by account and optional criteria with pagination.

        Args:
            account_id: Optional account ID to filter by. If None, returns all games
                (superadmin use case). Regular users should always pass account_id.
            pagination: Pagination parameters (required)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing games matching the filter criteria

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(GameORM).where(GameORM.deleted_at.is_(None))
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(GameORM.account_id == account_uuid)

        # Build filters dict for cursor validation
        filters_dict = {}

        # Future: Add additional filters here as needed
        # if "name" in kwargs:
        #     query = query.where(GameORM.name == kwargs["name"])
        #     filters_dict["name"] = kwargs["name"]

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
