"""Board repository services."""

from datetime import datetime
from typing import Any

from pydantic import UUID4
from sqlalchemy import func, select

from leadr.boards.adapters.orm import BoardORM, BoardTemplateORM
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.domain.board_template import BoardTemplate
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, BoardTemplateID, GameID, PrefixedID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository


class BoardRepository(BaseRepository[Board, BoardORM]):
    """Board repository for managing board persistence."""

    # Valid sortable fields for boards
    SORTABLE_FIELDS = {
        "id",
        "name",
        "slug",
        "short_code",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: BoardORM) -> Board:
        """Convert ORM model to domain entity."""
        return Board(
            id=BoardID(orm.id),
            account_id=AccountID(orm.account_id),
            game_id=GameID(orm.game_id),
            name=orm.name,
            slug=orm.slug,
            icon=orm.icon,
            short_code=orm.short_code,
            unit=orm.unit,
            is_active=orm.is_active,
            is_published=orm.is_published,
            sort_direction=SortDirection(orm.sort_direction),
            keep_strategy=KeepStrategy(orm.keep_strategy),
            created_from_template_id=BoardTemplateID(orm.created_from_template_id)
            if orm.created_from_template_id
            else None,
            template_name=orm.template_name,
            starts_at=orm.starts_at,
            ends_at=orm.ends_at,
            tags=orm.tags,
            description=orm.description,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: Board) -> BoardORM:
        """Convert domain entity to ORM model."""
        return BoardORM(
            id=entity.id.uuid,
            account_id=entity.account_id.uuid,
            game_id=entity.game_id.uuid,
            name=entity.name,
            slug=entity.slug,
            icon=entity.icon,
            short_code=entity.short_code,
            unit=entity.unit,
            is_active=entity.is_active,
            is_published=entity.is_published,
            sort_direction=entity.sort_direction.value,
            keep_strategy=entity.keep_strategy.value,
            created_from_template_id=entity.created_from_template_id.uuid
            if entity.created_from_template_id
            else None,
            template_name=entity.template_name,
            starts_at=entity.starts_at,
            ends_at=entity.ends_at,
            tags=entity.tags,
            description=entity.description,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[BoardORM]:
        """Get the ORM model class."""
        return BoardORM

    async def filter(
        self, account_id: UUID4 | PrefixedID | None = None, **kwargs: Any
    ) -> list[Board]:
        """Filter boards by account and optional criteria.

        Args:
            account_id: Optional account ID to filter by. If None, returns all boards
                (superadmin use case). Regular users should always pass account_id.
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of boards for the account matching the filter criteria
        """
        query = select(BoardORM).where(BoardORM.deleted_at.is_(None))
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(BoardORM.account_id == account_uuid)

        # Future: Add additional filters here as needed
        # if "game_id" in kwargs:
        #     query = query.where(BoardORM.game_id == kwargs["game_id"])

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def get_by_short_code(self, short_code: str) -> Board | None:
        """Get board by short_code.

        Args:
            short_code: The short_code to search for

        Returns:
            Board entity if found, None otherwise
        """
        return await self._get_by_field("short_code", short_code)

    async def get_by_slug(
        self,
        account_id: UUID4 | AccountID,
        game_id: UUID4 | GameID,
        slug: str,
        is_active: bool | None = None,
    ) -> Board | None:
        """Get board by slug within account and game scope.

        Lookups are scoped to account_id and game_id to respect the partial
        unique constraint (account_id, game_id, slug) WHERE is_active=true.

        Args:
            account_id: The account ID to filter by
            game_id: The game ID to filter by
            slug: The slug to search for
            is_active: Optional filter for active status. If None, returns board
                regardless of active status.

        Returns:
            Board entity if found, None otherwise
        """
        account_uuid = self._extract_uuid(account_id)
        game_uuid = self._extract_uuid(game_id)

        query = select(BoardORM).where(
            BoardORM.account_id == account_uuid,
            BoardORM.game_id == game_uuid,
            BoardORM.slug == slug,
            BoardORM.deleted_at.is_(None),
        )

        if is_active is not None:
            query = query.where(BoardORM.is_active == is_active)

        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_boards(
        self,
        account_id: UUID4 | AccountID | None = None,
        game_id: UUID4 | GameID | None = None,
        code: str | None = None,
        is_active: bool | None = None,
        is_published: bool | None = None,
        starts_before: datetime | None = None,
        starts_after: datetime | None = None,
        ends_before: datetime | None = None,
        ends_after: datetime | None = None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[Board]:
        """List boards with optional filtering and pagination.

        Args:
            account_id: Optional account ID to filter by
            game_id: Optional game ID to filter by
            code: Optional short code to filter by
            is_active: Optional filter for active status
            is_published: Optional filter for published status
            starts_before: Optional filter for boards starting before this time
            starts_after: Optional filter for boards starting after this time
            ends_before: Optional filter for boards ending before this time
            ends_after: Optional filter for boards ending after this time
            pagination: Pagination parameters (required)

        Returns:
            PaginatedResult containing boards matching the filter criteria

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(BoardORM).where(BoardORM.deleted_at.is_(None))

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(BoardORM.account_id == account_uuid)
            filters_dict["account_id"] = str(account_id)

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(BoardORM.game_id == game_uuid)
            filters_dict["game_id"] = str(game_id)

        if code is not None:
            query = query.where(BoardORM.short_code == code)
            filters_dict["code"] = code

        if is_active is not None:
            query = query.where(BoardORM.is_active == is_active)
            filters_dict["is_active"] = str(is_active)

        if is_published is not None:
            query = query.where(BoardORM.is_published == is_published)
            filters_dict["is_published"] = str(is_published)

        if starts_before is not None:
            query = query.where(BoardORM.starts_at <= starts_before)
            filters_dict["starts_before"] = starts_before.isoformat()

        if starts_after is not None:
            query = query.where(BoardORM.starts_at >= starts_after)
            filters_dict["starts_after"] = starts_after.isoformat()

        if ends_before is not None:
            query = query.where(BoardORM.ends_at <= ends_before)
            filters_dict["ends_before"] = ends_before.isoformat()

        if ends_after is not None:
            query = query.where(BoardORM.ends_at >= ends_after)
            filters_dict["ends_after"] = ends_after.isoformat()

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

    async def count_boards_by_template(self, template_id: BoardTemplateID) -> int:
        """Count boards created from a specific template.

        Args:
            template_id: The template ID to count boards for

        Returns:
            Number of boards created from this template
        """
        query = select(func.count()).where(
            BoardORM.created_from_template_id == template_id.uuid,
            BoardORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        count = result.scalar()
        return count or 0


class BoardTemplateRepository(BaseRepository[BoardTemplate, BoardTemplateORM]):
    """BoardTemplate repository for managing board template persistence."""

    # Valid sortable fields for board templates
    SORTABLE_FIELDS = {
        "id",
        "name",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: BoardTemplateORM) -> BoardTemplate:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: BoardTemplate) -> BoardTemplateORM:
        """Convert domain entity to ORM model."""
        return BoardTemplateORM.from_domain(entity)

    def _get_orm_class(self) -> type[BoardTemplateORM]:
        """Get the ORM model class."""
        return BoardTemplateORM

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[BoardTemplate]:
        """Filter board templates by account and optional game with pagination.

        Args:
            account_id: Optional account ID to filter by. If None, returns all templates
                (superadmin use case). Regular users should always pass account_id.
            game_id: OPTIONAL - Game ID to filter by
            pagination: Pagination parameters (required)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing board templates matching the filter criteria

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(BoardTemplateORM).where(BoardTemplateORM.deleted_at.is_(None))
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(BoardTemplateORM.account_id == account_uuid)

        # Build filters dict for cursor validation
        filters_dict = {}

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(BoardTemplateORM.game_id == game_uuid)
            filters_dict["game_id"] = str(game_id)

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
