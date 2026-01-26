"""Board repository services."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from leadr.boards.adapters.orm import (
    BoardORM,
    BoardRatioConfigORM,
    BoardStateORM,
    BoardTemplateORM,
    BoardTypeEnum,
    KeepStrategyEnum,
    RatioDisplayEnum,
    RunEntryORM,
    TieBreakerEnum,
    ZeroDenominatorPolicyEnum,
)
from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    TieBreaker,
    ZeroDenominatorPolicy,
)
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.board_template import BoardTemplate
from leadr.boards.domain.run_entry import RunEntry
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    BoardRatioConfigID,
    BoardStateID,
    BoardTemplateID,
    GameID,
    IdentityID,
    RunEntryID,
    ScoreEventID,
)
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
            board_type=BoardType(orm.board_type.value),
            keep_strategy=KeepStrategy(orm.keep_strategy.value),
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
            board_type=BoardTypeEnum(entity.board_type.value),
            keep_strategy=KeepStrategyEnum(entity.keep_strategy.value),
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

    async def get_by_short_code(self, short_code: str) -> Board | None:
        """Get board by short_code.

        Args:
            short_code: The short_code to search for

        Returns:
            Board entity if found, None otherwise
        """
        return await self._get_by_field("short_code", short_code)

    async def filter(
        self,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        code: str | None = None,
        slug: str | None = None,
        is_active: bool | None = None,
        is_published: bool | None = None,
        starts_before: datetime | None = None,
        starts_after: datetime | None = None,
        ends_before: datetime | None = None,
        ends_after: datetime | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[Board]:
        """Filter boards with optional criteria and pagination.

        Args:
            account_id: Optional account ID to filter by
            game_id: Optional game ID to filter by
            code: Optional short code to filter by
            slug: Optional slug to filter by
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

        if slug is not None:
            query = query.where(BoardORM.slug == slug)
            filters_dict["slug"] = slug

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

    async def filter(
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


class BoardStateRepository(BaseRepository[BoardState, BoardStateORM]):
    """BoardState repository for managing board state persistence.

    Board states represent the materialized ranking state for identities on boards.
    Each identity has at most one state per board.
    """

    # Valid sortable fields for board states
    SORTABLE_FIELDS = {
        "id",
        "primary_value",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: BoardStateORM) -> BoardState:
        """Convert ORM model to domain entity."""
        return BoardState(
            id=BoardStateID(orm.id),
            board_id=BoardID(orm.board_id),
            identity_id=IdentityID(orm.identity_id),
            primary_value=orm.primary_value,
            aux=orm.aux,
            player_name=orm.player_name,
            is_test=orm.is_test,
            timezone=orm.timezone,
            country=orm.country,
            city=orm.city,
            value_display=orm.value_display,
            metadata=orm.state_metadata,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: BoardState) -> BoardStateORM:
        """Convert domain entity to ORM model."""
        return BoardStateORM(
            id=entity.id.uuid,
            board_id=entity.board_id.uuid,
            identity_id=entity.identity_id.uuid,
            primary_value=entity.primary_value,
            aux=entity.aux,
            player_name=entity.player_name,
            is_test=entity.is_test,
            timezone=entity.timezone,
            country=entity.country,
            city=entity.city,
            value_display=entity.value_display,
            state_metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[BoardStateORM]:
        """Get the ORM model class."""
        return BoardStateORM

    async def get_by_board_and_identity(
        self,
        board_id: BoardID,
        identity_id: IdentityID,
    ) -> BoardState | None:
        """Get a board state by board and identity.

        Args:
            board_id: The board ID to search for.
            identity_id: The identity ID to search for.

        Returns:
            BoardState entity if found, None otherwise.
        """
        query = select(BoardStateORM).where(
            BoardStateORM.board_id == board_id.uuid,
            BoardStateORM.identity_id == identity_id.uuid,
            BoardStateORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def filter(  # type: ignore[override] - board states filter by board_id, not account_id
        self,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[BoardState]:
        """Filter board states with optional criteria and pagination.

        Args:
            board_id: Optional board ID to filter by.
            identity_id: Optional identity ID to filter by.
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing board states matching the filter criteria.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS.
            CursorValidationError: If cursor is invalid or state doesn't match.
        """
        query = select(BoardStateORM).where(BoardStateORM.deleted_at.is_(None))

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(BoardStateORM.board_id == board_uuid)
            filters_dict["board_id"] = str(board_id)

        if identity_id is not None:
            identity_uuid = self._extract_uuid(identity_id)
            query = query.where(BoardStateORM.identity_id == identity_uuid)
            filters_dict["identity_id"] = str(identity_id)

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


class RunEntryRepository(BaseRepository[RunEntry, RunEntryORM]):
    """RunEntry repository for managing run entry persistence.

    Run entries represent individual scored submissions for RUN_RUNS boards
    where every submission is ranked.
    """

    # Valid sortable fields for run entries
    SORTABLE_FIELDS = {
        "id",
        "primary_value",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: RunEntryORM) -> RunEntry:
        """Convert ORM model to domain entity."""
        return RunEntry(
            id=RunEntryID(orm.id),
            board_id=BoardID(orm.board_id),
            identity_id=IdentityID(orm.identity_id),
            score_event_id=ScoreEventID(orm.score_event_id),
            primary_value=orm.primary_value,
            player_name=orm.player_name,
            is_test=orm.is_test,
            timezone=orm.timezone,
            country=orm.country,
            city=orm.city,
            value_display=orm.value_display,
            metadata=orm.entry_metadata,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: RunEntry) -> RunEntryORM:
        """Convert domain entity to ORM model."""
        return RunEntryORM(
            id=entity.id.uuid,
            board_id=entity.board_id.uuid,
            identity_id=entity.identity_id.uuid,
            score_event_id=entity.score_event_id.uuid,
            primary_value=entity.primary_value,
            player_name=entity.player_name,
            is_test=entity.is_test,
            timezone=entity.timezone,
            country=entity.country,
            city=entity.city,
            value_display=entity.value_display,
            entry_metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[RunEntryORM]:
        """Get the ORM model class."""
        return RunEntryORM

    async def get_by_board_and_score_event(
        self,
        board_id: BoardID,
        score_event_id: ScoreEventID,
    ) -> RunEntry | None:
        """Get a run entry by board and score event.

        Args:
            board_id: The board ID to search for.
            score_event_id: The score event ID to search for.

        Returns:
            RunEntry entity if found, None otherwise.
        """
        query = select(RunEntryORM).where(
            RunEntryORM.board_id == board_id.uuid,
            RunEntryORM.score_event_id == score_event_id.uuid,
            RunEntryORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def filter(  # type: ignore[override] - run entries filter by board_id, not account_id
        self,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[RunEntry]:
        """Filter run entries with optional criteria and pagination.

        Args:
            board_id: Optional board ID to filter by.
            identity_id: Optional identity ID to filter by.
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing run entries matching the filter criteria.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS.
            CursorValidationError: If cursor is invalid or state doesn't match.
        """
        query = select(RunEntryORM).where(RunEntryORM.deleted_at.is_(None))

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(RunEntryORM.board_id == board_uuid)
            filters_dict["board_id"] = str(board_id)

        if identity_id is not None:
            identity_uuid = self._extract_uuid(identity_id)
            query = query.where(RunEntryORM.identity_id == identity_uuid)
            filters_dict["identity_id"] = str(identity_id)

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


class BoardRatioConfigRepository(BaseRepository[BoardRatioConfig, BoardRatioConfigORM]):
    """Repository for BoardRatioConfig persistence."""

    SORTABLE_FIELDS = {"id", "created_at", "updated_at"}

    def _to_domain(self, orm: BoardRatioConfigORM) -> BoardRatioConfig:
        """Convert ORM model to domain entity."""
        # Handle enum values (may be str when ORM created directly, or enum when from DB)
        zero_policy = (
            orm.zero_denominator_policy
            if isinstance(orm.zero_denominator_policy, str)
            else orm.zero_denominator_policy.value
        )
        display = orm.display if isinstance(orm.display, str) else orm.display.value
        tie_breaker = orm.tie_breaker if isinstance(orm.tie_breaker, str) else orm.tie_breaker.value

        return BoardRatioConfig(
            id=BoardRatioConfigID(orm.id),
            board_id=BoardID(orm.board_id),
            numerator_board_id=BoardID(orm.numerator_board_id),
            denominator_board_id=BoardID(orm.denominator_board_id),
            zero_denominator_policy=ZeroDenominatorPolicy(zero_policy),
            min_denominator=orm.min_denominator,
            min_numerator=orm.min_numerator,
            scale=orm.scale,
            display=RatioDisplay(display),
            decimals=orm.decimals,
            tie_breaker=TieBreaker(tie_breaker),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: BoardRatioConfig) -> BoardRatioConfigORM:
        """Convert domain entity to ORM model."""
        return BoardRatioConfigORM(
            id=entity.id.uuid,
            board_id=entity.board_id.uuid,
            numerator_board_id=entity.numerator_board_id.uuid,
            denominator_board_id=entity.denominator_board_id.uuid,
            zero_denominator_policy=ZeroDenominatorPolicyEnum(entity.zero_denominator_policy.value),
            min_denominator=entity.min_denominator,
            min_numerator=entity.min_numerator,
            scale=entity.scale,
            display=RatioDisplayEnum(entity.display.value),
            decimals=entity.decimals,
            tie_breaker=TieBreakerEnum(entity.tie_breaker.value),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[BoardRatioConfigORM]:
        """Return the ORM class for this repository."""
        return BoardRatioConfigORM

    async def get_by_board_id(self, board_id: BoardID) -> BoardRatioConfig | None:
        """Get the ratio config for a specific board.

        Args:
            board_id: The ID of the ratio board.

        Returns:
            BoardRatioConfig if found, None otherwise.
        """
        query = select(BoardRatioConfigORM).where(
            BoardRatioConfigORM.board_id == board_id.uuid,
            BoardRatioConfigORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def filter(  # type: ignore[override] - ratio configs filter by board_id, not account_id
        self,
        board_id: BoardID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[BoardRatioConfig]:
        """Filter ratio configs with optional criteria and pagination.

        Args:
            board_id: Optional board ID to filter by.
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing ratio configs matching the filter criteria.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS.
            CursorValidationError: If cursor is invalid or state doesn't match.
        """
        query = select(BoardRatioConfigORM).where(BoardRatioConfigORM.deleted_at.is_(None))

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(BoardRatioConfigORM.board_id == board_uuid)
            filters_dict["board_id"] = str(board_id)

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
