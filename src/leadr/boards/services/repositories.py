"""Board repository services."""

from typing import Any, overload

from pydantic import UUID4
from sqlalchemy import select

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
            icon=orm.icon,
            short_code=orm.short_code,
            unit=orm.unit,
            is_active=orm.is_active,
            sort_direction=SortDirection(orm.sort_direction),
            keep_strategy=KeepStrategy(orm.keep_strategy),
            template_id=BoardTemplateID(orm.template_id) if orm.template_id else None,
            template_name=orm.template_name,
            starts_at=orm.starts_at,
            ends_at=orm.ends_at,
            tags=orm.tags,
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
            icon=entity.icon,
            short_code=entity.short_code,
            unit=entity.unit,
            is_active=entity.is_active,
            sort_direction=entity.sort_direction.value,
            keep_strategy=entity.keep_strategy.value,
            template_id=entity.template_id.uuid if entity.template_id else None,
            template_name=entity.template_name,
            starts_at=entity.starts_at,
            ends_at=entity.ends_at,
            tags=entity.tags,
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
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of boards for the account matching the filter criteria

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering boards")
        account_uuid = self._extract_uuid(account_id)
        query = select(BoardORM).where(
            BoardORM.account_id == account_uuid,
            BoardORM.deleted_at.is_(None),
        )

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

    @overload
    async def list_boards(
        self,
        account_id: UUID4 | AccountID | None = None,
        code: str | None = None,
        pagination: None = None,
    ) -> list[Board]: ...

    @overload
    async def list_boards(
        self,
        account_id: UUID4 | AccountID | None = None,
        code: str | None = None,
        pagination: PaginationParams = ...,
    ) -> PaginatedResult[Board]: ...

    async def list_boards(
        self,
        account_id: UUID4 | AccountID | None = None,
        code: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Board] | PaginatedResult[Board]:
        """List boards with optional filtering by account_id and/or code.

        This method supports special behavior for superadmins filtering by code only.

        Args:
            account_id: Optional account ID to filter by
            code: Optional short code to filter by
            pagination: Optional pagination parameters

        Returns:
            List of boards if no pagination, PaginatedResult if pagination provided

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(BoardORM).where(BoardORM.deleted_at.is_(None))

        # Build filters dict for cursor validation
        filters_dict = {}

        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(BoardORM.account_id == account_uuid)
            filters_dict["account_id"] = str(account_id)

        if code is not None:
            query = query.where(BoardORM.short_code == code)
            filters_dict["code"] = code

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

    @overload
    async def filter(
        self,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        pagination: None = None,
        **kwargs: Any,
    ) -> list[BoardTemplate]: ...

    @overload
    async def filter(
        self,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        pagination: PaginationParams = ...,
        **kwargs: Any,
    ) -> PaginatedResult[BoardTemplate]: ...

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        pagination: PaginationParams | None = None,
        **kwargs: Any,
    ) -> list[BoardTemplate] | PaginatedResult[BoardTemplate]:
        """Filter board templates by account and optional game.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            game_id: OPTIONAL - Game ID to filter by
            pagination: Optional pagination parameters
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of board templates if no pagination, PaginatedResult if pagination provided

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering board templates")
        account_uuid = self._extract_uuid(account_id)
        query = select(BoardTemplateORM).where(
            BoardTemplateORM.account_id == account_uuid,
            BoardTemplateORM.deleted_at.is_(None),
        )

        # Build filters dict for cursor validation
        filters_dict = {}

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(BoardTemplateORM.game_id == game_uuid)
            filters_dict["game_id"] = str(game_id)

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
