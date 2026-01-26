"""Board repository services."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select

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
from leadr.common.domain.pagination import SortDirection as PaginationSortDirection
from leadr.common.domain.pagination import SortField
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
        is_test: bool | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[BoardState]:
        """Filter board states with optional criteria and pagination.

        Args:
            board_id: Optional board ID to filter by.
            identity_id: Optional identity ID to filter by.
            is_test: Optional filter for test entries (True=test only, False=prod only, None=all).
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

        if is_test is not None:
            query = query.where(BoardStateORM.is_test == is_test)
            filters_dict["is_test"] = str(is_test)

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

    async def get_rank(
        self,
        state: BoardState,
        sort_fields: "list[SortField]",
    ) -> int:
        """Compute rank for a board state using COUNT approach.

        Counts how many entries rank better than the given state using the
        same multi-field comparison logic used for sorting.

        Args:
            state: BoardState to compute rank for.
            sort_fields: Sort fields defining the ranking order.

        Returns:
            Rank (1-indexed, where 1 is the best).
        """
        target_values = self._extract_target_values(state, sort_fields)

        # Build condition for "entries that rank better"
        better_condition = self._build_position_clause(
            target_values=target_values,
            sort_fields=sort_fields,
            before_target=True,  # Entries that come BEFORE target = better ranked
        )

        # Count entries that rank better (within same board, not deleted)
        count_query = (
            select(func.count())
            .select_from(BoardStateORM)
            .where(BoardStateORM.deleted_at.is_(None))
            .where(BoardStateORM.board_id == state.board_id.uuid)
            .where(BoardStateORM.is_test == state.is_test)
            .where(better_condition)
        )

        result = await self.session.execute(count_query)
        better_count = result.scalar_one()

        return better_count + 1  # Rank is 1-indexed

    def _extract_target_values(
        self,
        state: BoardState,
        sort_fields: "list[SortField]",
    ) -> dict[str, Any]:
        """Extract values from target state for each sort field.

        Args:
            state: The target BoardState entity.
            sort_fields: List of sort fields.

        Returns:
            Dict mapping field names to their values from the target state.
        """
        values: dict[str, Any] = {}
        for sort_field in sort_fields:
            value = getattr(state, sort_field.name)
            # For ID fields, extract the UUID
            if hasattr(value, "uuid"):
                value = value.uuid
            values[sort_field.name] = value
        return values

    def _build_position_clause(
        self,
        target_values: dict[str, Any],
        sort_fields: "list[SortField]",
        before_target: bool,
    ) -> Any:
        """Build WHERE clause for rows before or after target position.

        This creates a compound comparison clause that respects the multi-field sort.
        For (value DESC, created_at DESC, id ASC) looking for rows BEFORE target:
        - value > target_value
        - OR (value = target_value AND created_at > target_created_at)
        - OR (value = target_value AND created_at = target_created_at AND id < target_id)

        Args:
            target_values: Dict of sort field values from target state.
            sort_fields: List of sort fields.
            before_target: True for rows before target (better ranked), False for after.

        Returns:
            SQLAlchemy WHERE clause.
        """
        or_conditions = []

        for i, sort_field in enumerate(sort_fields):
            # Determine comparison operator
            # For DESC: "before" means greater value, "after" means lesser value
            # For ASC: "before" means lesser value, "after" means greater value
            if before_target:
                if sort_field.direction == PaginationSortDirection.DESC:
                    comp_op = "__gt__"
                else:
                    comp_op = "__lt__"
            else:
                if sort_field.direction == PaginationSortDirection.DESC:
                    comp_op = "__lt__"
                else:
                    comp_op = "__gt__"

            # Build equality conditions for all previous fields
            equality_conditions = []
            for j in range(i):
                prev_field = sort_fields[j]
                prev_column = self._get_orm_column(prev_field.name)
                prev_value = target_values[prev_field.name]
                equality_conditions.append(prev_column == prev_value)

            # Add comparison condition for current field
            current_column = self._get_orm_column(sort_field.name)
            current_value = target_values[sort_field.name]
            comparison = getattr(current_column, comp_op)(current_value)

            # Combine: all previous equals AND current comparison
            if equality_conditions:
                or_conditions.append(and_(*equality_conditions, comparison))
            else:
                or_conditions.append(comparison)

        return or_(*or_conditions)

    def _invert_sort_fields(self, sort_fields: "list[SortField]") -> "list[SortField]":
        """Invert the direction of all sort fields.

        Used for "above" queries where we need results closest to target first.

        Args:
            sort_fields: Original sort fields.

        Returns:
            New list with inverted sort directions.
        """
        return [
            SortField(
                name=f.name,
                direction=PaginationSortDirection.ASC
                if f.direction == PaginationSortDirection.DESC
                else PaginationSortDirection.DESC,
            )
            for f in sort_fields
        ]

    def _apply_sort(self, query: Any, sort_fields: "list[SortField]") -> Any:
        """Apply sort order to query.

        Args:
            query: SQLAlchemy query to sort.
            sort_fields: Sort fields to apply.

        Returns:
            Query with ORDER BY applied.
        """
        order_by_clauses = []
        for sf in sort_fields:
            column = self._get_orm_column(sf.name)
            if sf.direction == PaginationSortDirection.DESC:
                order_by_clauses.append(column.desc())
            else:
                order_by_clauses.append(column.asc())
        return query.order_by(*order_by_clauses)

    async def execute_around_query(
        self,
        board_id: BoardID,
        target_state: BoardState,
        sort_fields: "list[SortField]",
        limit: int,
        is_test: bool | None = None,
    ) -> PaginatedResult[BoardState]:
        """Execute a query that returns states centered around a target state.

        This method fetches states in a window around the target state, respecting
        the sort order. For limit=5 with DESC sort, it returns 2 states above
        (better ranked), the target, and 2 states below (worse ranked).

        When the target is near an edge, the window adjusts to fill up to the limit.

        Args:
            board_id: Board ID to filter by.
            target_state: The state to center results around.
            sort_fields: Sort fields defining the ranking order.
            limit: Total number of states to return (including target).
            is_test: Optional filter for test entries.

        Returns:
            PaginatedResult with states centered around target.
        """
        # Calculate window sizes
        ideal_above_count = limit // 2
        ideal_below_count = limit - ideal_above_count - 1
        max_side_items = limit - 1

        # Extract target position values
        target_values = self._extract_target_values(target_state, sort_fields)

        # Build base query
        base_query = select(BoardStateORM).where(
            BoardStateORM.deleted_at.is_(None),
            BoardStateORM.board_id == board_id.uuid,
        )
        if is_test is not None:
            base_query = base_query.where(BoardStateORM.is_test == is_test)
        else:
            # Filter by same test status as target
            base_query = base_query.where(BoardStateORM.is_test == target_state.is_test)

        # Build "above" query (better ranked, closest first)
        above_clause = self._build_position_clause(target_values, sort_fields, before_target=True)
        above_query = base_query.where(above_clause)
        above_query = self._apply_sort(above_query, self._invert_sort_fields(sort_fields))
        above_query = above_query.limit(max_side_items + 1)

        # Build "below" query (worse ranked, closest first)
        below_clause = self._build_position_clause(target_values, sort_fields, before_target=False)
        below_query = base_query.where(below_clause)
        below_query = self._apply_sort(below_query, sort_fields)
        below_query = below_query.limit(max_side_items + 1)

        # Execute both queries
        above_result = await self.session.execute(above_query)
        above_orms = list(above_result.scalars().all())

        below_result = await self.session.execute(below_query)
        below_orms = list(below_result.scalars().all())

        # Adjust window sizes based on available items
        available_above = len(above_orms)
        available_below = len(below_orms)

        if available_above < ideal_above_count:
            actual_above_count = available_above
            actual_below_count = min(available_below, limit - 1 - actual_above_count)
        elif available_below < ideal_below_count:
            actual_below_count = available_below
            actual_above_count = min(available_above, limit - 1 - actual_below_count)
        else:
            actual_above_count = ideal_above_count
            actual_below_count = ideal_below_count

        # Determine pagination flags
        has_prev = available_above > actual_above_count
        has_next = available_below > actual_below_count

        # Trim to adjusted window sizes
        above_orms = above_orms[:actual_above_count]
        below_orms = below_orms[:actual_below_count]

        # Reverse above results (they were fetched closest-first, need best-first)
        above_orms.reverse()

        # Build results: above items + target + below items
        items: list[BoardState] = [self._to_domain(orm) for orm in above_orms]
        items.append(target_state)
        items.extend(self._to_domain(orm) for orm in below_orms)

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=None,  # Cursor not supported for around queries
            prev_position=None,
        )

    async def execute_around_value_query(
        self,
        board_id: BoardID,
        target_value: float,
        sort_fields: "list[SortField]",
        limit: int,
        is_test: bool | None = None,
    ) -> PaginatedResult[BoardState]:
        """Execute a query that returns states centered around a hypothetical value.

        Creates a synthetic placeholder state with the given value and returns it
        along with neighboring states. The placeholder has is_placeholder=True and
        uses sentinel nil UUIDs for id and identity_id.

        Args:
            board_id: Board ID to filter by.
            target_value: The hypothetical score value to center results around.
            sort_fields: Sort fields defining the ranking order.
            limit: Total number of states to return (including placeholder).
            is_test: Optional filter for test entries.

        Returns:
            PaginatedResult with states centered around value (including placeholder).
        """
        # nil UUID for placeholder
        nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
        now = datetime.now(UTC)

        # Determine is_test for placeholder and query filtering
        test_filter = is_test if is_test is not None else False

        # Create placeholder state
        placeholder = BoardState(
            id=BoardStateID(nil_uuid),
            board_id=board_id,
            identity_id=IdentityID(nil_uuid),
            primary_value=target_value,
            is_test=test_filter,
            is_placeholder=True,
            created_at=now,
            updated_at=now,
        )

        # Compute placeholder's hypothetical rank
        placeholder_rank = await self._get_value_rank(target_value, board_id, sort_fields, is_test)
        placeholder.rank = placeholder_rank

        # Calculate window sizes
        ideal_above_count = limit // 2
        ideal_below_count = limit - ideal_above_count - 1
        max_side_items = limit - 1

        # Build base query
        base_query = select(BoardStateORM).where(
            BoardStateORM.deleted_at.is_(None),
            BoardStateORM.board_id == board_id.uuid,
        )
        if is_test is not None:
            base_query = base_query.where(BoardStateORM.is_test == is_test)

        # Extract placeholder position values
        target_values = self._extract_target_values(placeholder, sort_fields)

        # Build "above" query (better ranked, closest first)
        above_clause = self._build_position_clause(target_values, sort_fields, before_target=True)
        above_query = base_query.where(above_clause)
        above_query = self._apply_sort(above_query, self._invert_sort_fields(sort_fields))
        above_query = above_query.limit(max_side_items + 1)

        # Build "below" query (worse ranked, closest first)
        # For placeholder with newest timestamp, all same-value entries are "below"
        below_clause = self._build_position_clause_for_value(target_values, sort_fields)
        below_query = base_query.where(below_clause)
        below_query = self._apply_sort(below_query, sort_fields)
        below_query = below_query.limit(max_side_items + 1)

        # Execute both queries
        above_result = await self.session.execute(above_query)
        above_orms = list(above_result.scalars().all())

        below_result = await self.session.execute(below_query)
        below_orms = list(below_result.scalars().all())

        # Adjust window sizes based on available items
        available_above = len(above_orms)
        available_below = len(below_orms)

        if available_above < ideal_above_count:
            actual_above_count = available_above
            actual_below_count = min(available_below, limit - 1 - actual_above_count)
        elif available_below < ideal_below_count:
            actual_below_count = available_below
            actual_above_count = min(available_above, limit - 1 - actual_below_count)
        else:
            actual_above_count = ideal_above_count
            actual_below_count = ideal_below_count

        # Determine pagination flags
        has_prev = available_above > actual_above_count
        has_next = available_below > actual_below_count

        # Trim to adjusted window sizes
        above_orms = above_orms[:actual_above_count]
        below_orms = below_orms[:actual_below_count]

        # Reverse above results (they were fetched closest-first, need best-first)
        above_orms.reverse()

        # Build results with computed ranks
        items: list[BoardState] = []

        # Add above items with ranks
        for i, orm in enumerate(above_orms):
            state = self._to_domain(orm)
            state.rank = placeholder_rank - (actual_above_count - i)
            items.append(state)

        # Add placeholder
        items.append(placeholder)

        # Add below items with ranks
        for i, orm in enumerate(below_orms):
            state = self._to_domain(orm)
            state.rank = placeholder_rank + i + 1
            items.append(state)

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=None,
            prev_position=None,
        )

    async def _get_value_rank(
        self,
        value: float,
        board_id: BoardID,
        sort_fields: "list[SortField]",
        is_test: bool | None = None,
    ) -> int:
        """Compute hypothetical rank for a value using COUNT approach.

        Counts how many states rank better than the given value.
        For a placeholder (newest timestamp), scores with the same value
        are counted as "below" since the placeholder would be at the top
        of any same-value group.

        Args:
            value: The score value to compute rank for.
            board_id: Board ID to filter by.
            sort_fields: Sort fields defining the ranking order.
            is_test: Optional filter for test entries.

        Returns:
            Rank (1-indexed, where 1 is the best).
        """
        # Get the primary sort field (should be "primary_value")
        primary_field = sort_fields[0]
        value_column = self._get_orm_column(primary_field.name)

        # For DESC: better means value > target
        # For ASC: better means value < target
        if primary_field.direction == PaginationSortDirection.DESC:
            better_condition = value_column > value
        else:
            better_condition = value_column < value

        # Count states that rank better
        count_query = (
            select(func.count())
            .select_from(BoardStateORM)
            .where(BoardStateORM.deleted_at.is_(None))
            .where(BoardStateORM.board_id == board_id.uuid)
            .where(better_condition)
        )

        if is_test is not None:
            count_query = count_query.where(BoardStateORM.is_test == is_test)

        result = await self.session.execute(count_query)
        better_count = result.scalar_one()

        return better_count + 1

    def _build_position_clause_for_value(
        self,
        target_values: dict[str, Any],
        sort_fields: "list[SortField]",
    ) -> Any:
        """Build WHERE clause for rows after a hypothetical value position.

        For a placeholder with the newest timestamp, scores that rank "below" are:
        - Scores with worse value (according to sort direction)
        - Scores with same value (since placeholder has newest created_at)

        Args:
            target_values: Dict of sort field values from placeholder.
            sort_fields: List of sort fields.

        Returns:
            SQLAlchemy WHERE clause.
        """
        # Get the primary sort field (should be "primary_value")
        primary_field = sort_fields[0]
        value_column = self._get_orm_column(primary_field.name)
        target_value = target_values[primary_field.name]

        # For DESC: below means value <= target (same or worse)
        # For ASC: below means value >= target (same or worse)
        if primary_field.direction == PaginationSortDirection.DESC:
            return value_column <= target_value
        else:
            return value_column >= target_value


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
        is_test: bool | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[RunEntry]:
        """Filter run entries with optional criteria and pagination.

        Args:
            board_id: Optional board ID to filter by.
            identity_id: Optional identity ID to filter by.
            is_test: Optional filter for test entries (True=test only, False=prod only, None=all).
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

        if is_test is not None:
            query = query.where(RunEntryORM.is_test == is_test)
            filters_dict["is_test"] = str(is_test)

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

    async def get_rank(
        self,
        entry: RunEntry,
        sort_fields: "list[SortField]",
    ) -> int:
        """Compute rank for a run entry using COUNT approach.

        Counts how many entries rank better than the given entry using the
        same multi-field comparison logic used for sorting.

        Args:
            entry: RunEntry to compute rank for.
            sort_fields: Sort fields defining the ranking order.

        Returns:
            Rank (1-indexed, where 1 is the best).
        """
        target_values = self._extract_target_values(entry, sort_fields)

        # Build condition for "entries that rank better"
        better_condition = self._build_position_clause(
            target_values=target_values,
            sort_fields=sort_fields,
            before_target=True,  # Entries that come BEFORE target = better ranked
        )

        # Count entries that rank better (within same board, not deleted)
        count_query = (
            select(func.count())
            .select_from(RunEntryORM)
            .where(RunEntryORM.deleted_at.is_(None))
            .where(RunEntryORM.board_id == entry.board_id.uuid)
            .where(RunEntryORM.is_test == entry.is_test)
            .where(better_condition)
        )

        result = await self.session.execute(count_query)
        better_count = result.scalar_one()

        return better_count + 1  # Rank is 1-indexed

    def _extract_target_values(
        self,
        entry: RunEntry,
        sort_fields: "list[SortField]",
    ) -> dict[str, Any]:
        """Extract values from target entry for each sort field.

        Args:
            entry: The target RunEntry entity.
            sort_fields: List of sort fields.

        Returns:
            Dict mapping field names to their values from the target entry.
        """
        values: dict[str, Any] = {}
        for sort_field in sort_fields:
            value = getattr(entry, sort_field.name)
            # For ID fields, extract the UUID
            if hasattr(value, "uuid"):
                value = value.uuid
            values[sort_field.name] = value
        return values

    def _build_position_clause(
        self,
        target_values: dict[str, Any],
        sort_fields: "list[SortField]",
        before_target: bool,
    ) -> Any:
        """Build WHERE clause for rows before or after target position.

        This creates a compound comparison clause that respects the multi-field sort.

        Args:
            target_values: Dict of sort field values from target entry.
            sort_fields: List of sort fields.
            before_target: True for rows before target (better ranked), False for after.

        Returns:
            SQLAlchemy WHERE clause.
        """
        or_conditions = []

        for i, sort_field in enumerate(sort_fields):
            # Determine comparison operator
            # For DESC: "before" means greater value, "after" means lesser value
            # For ASC: "before" means lesser value, "after" means greater value
            if before_target:
                if sort_field.direction == PaginationSortDirection.DESC:
                    comp_op = "__gt__"
                else:
                    comp_op = "__lt__"
            else:
                if sort_field.direction == PaginationSortDirection.DESC:
                    comp_op = "__lt__"
                else:
                    comp_op = "__gt__"

            # Build equality conditions for all previous fields
            equality_conditions = []
            for j in range(i):
                prev_field = sort_fields[j]
                prev_column = self._get_orm_column(prev_field.name)
                prev_value = target_values[prev_field.name]
                equality_conditions.append(prev_column == prev_value)

            # Add comparison condition for current field
            current_column = self._get_orm_column(sort_field.name)
            current_value = target_values[sort_field.name]
            comparison = getattr(current_column, comp_op)(current_value)

            # Combine: all previous equals AND current comparison
            if equality_conditions:
                or_conditions.append(and_(*equality_conditions, comparison))
            else:
                or_conditions.append(comparison)

        return or_(*or_conditions)

    def _invert_sort_fields(self, sort_fields: "list[SortField]") -> "list[SortField]":
        """Invert the direction of all sort fields.

        Used for "above" queries where we need results closest to target first.

        Args:
            sort_fields: Original sort fields.

        Returns:
            New list with inverted sort directions.
        """
        return [
            SortField(
                name=f.name,
                direction=PaginationSortDirection.ASC
                if f.direction == PaginationSortDirection.DESC
                else PaginationSortDirection.DESC,
            )
            for f in sort_fields
        ]

    def _apply_sort(self, query: Any, sort_fields: "list[SortField]") -> Any:
        """Apply sort order to query.

        Args:
            query: SQLAlchemy query to sort.
            sort_fields: Sort fields to apply.

        Returns:
            Query with ORDER BY applied.
        """
        order_by_clauses = []
        for sf in sort_fields:
            column = self._get_orm_column(sf.name)
            if sf.direction == PaginationSortDirection.DESC:
                order_by_clauses.append(column.desc())
            else:
                order_by_clauses.append(column.asc())
        return query.order_by(*order_by_clauses)

    async def execute_around_query(
        self,
        board_id: BoardID,
        target_entry: RunEntry,
        sort_fields: "list[SortField]",
        limit: int,
        is_test: bool | None = None,
    ) -> PaginatedResult[RunEntry]:
        """Execute a query that returns entries centered around a target entry.

        This method fetches entries in a window around the target entry, respecting
        the sort order. For limit=5 with DESC sort, it returns 2 entries above
        (better ranked), the target, and 2 entries below (worse ranked).

        When the target is near an edge, the window adjusts to fill up to the limit.

        Args:
            board_id: Board ID to filter by.
            target_entry: The entry to center results around.
            sort_fields: Sort fields defining the ranking order.
            limit: Total number of entries to return (including target).
            is_test: Optional filter for test entries.

        Returns:
            PaginatedResult with entries centered around target.
        """
        # Calculate window sizes
        ideal_above_count = limit // 2
        ideal_below_count = limit - ideal_above_count - 1
        max_side_items = limit - 1

        # Extract target position values
        target_values = self._extract_target_values(target_entry, sort_fields)

        # Build base query
        base_query = select(RunEntryORM).where(
            RunEntryORM.deleted_at.is_(None),
            RunEntryORM.board_id == board_id.uuid,
        )
        if is_test is not None:
            base_query = base_query.where(RunEntryORM.is_test == is_test)
        else:
            # Filter by same test status as target
            base_query = base_query.where(RunEntryORM.is_test == target_entry.is_test)

        # Build "above" query (better ranked, closest first)
        above_clause = self._build_position_clause(target_values, sort_fields, before_target=True)
        above_query = base_query.where(above_clause)
        above_query = self._apply_sort(above_query, self._invert_sort_fields(sort_fields))
        above_query = above_query.limit(max_side_items + 1)

        # Build "below" query (worse ranked, closest first)
        below_clause = self._build_position_clause(target_values, sort_fields, before_target=False)
        below_query = base_query.where(below_clause)
        below_query = self._apply_sort(below_query, sort_fields)
        below_query = below_query.limit(max_side_items + 1)

        # Execute both queries
        above_result = await self.session.execute(above_query)
        above_orms = list(above_result.scalars().all())

        below_result = await self.session.execute(below_query)
        below_orms = list(below_result.scalars().all())

        # Adjust window sizes based on available items
        available_above = len(above_orms)
        available_below = len(below_orms)

        if available_above < ideal_above_count:
            actual_above_count = available_above
            actual_below_count = min(available_below, limit - 1 - actual_above_count)
        elif available_below < ideal_below_count:
            actual_below_count = available_below
            actual_above_count = min(available_above, limit - 1 - actual_below_count)
        else:
            actual_above_count = ideal_above_count
            actual_below_count = ideal_below_count

        # Determine pagination flags
        has_prev = available_above > actual_above_count
        has_next = available_below > actual_below_count

        # Trim to adjusted window sizes
        above_orms = above_orms[:actual_above_count]
        below_orms = below_orms[:actual_below_count]

        # Reverse above results (they were fetched closest-first, need best-first)
        above_orms.reverse()

        # Build results: above items + target + below items
        items: list[RunEntry] = [self._to_domain(orm) for orm in above_orms]
        items.append(target_entry)
        items.extend(self._to_domain(orm) for orm in below_orms)

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=None,  # Cursor not supported for around queries
            prev_position=None,
        )

    async def execute_around_value_query(
        self,
        board_id: BoardID,
        target_value: float,
        sort_fields: "list[SortField]",
        limit: int,
        is_test: bool | None = None,
    ) -> PaginatedResult[RunEntry]:
        """Execute a query that returns entries centered around a hypothetical value.

        Creates a synthetic placeholder entry with the given value and returns it
        along with neighboring entries. The placeholder has is_placeholder=True and
        uses sentinel nil UUIDs for id and identity_id.

        Args:
            board_id: Board ID to filter by.
            target_value: The hypothetical score value to center results around.
            sort_fields: Sort fields defining the ranking order.
            limit: Total number of entries to return (including placeholder).
            is_test: Optional filter for test entries.

        Returns:
            PaginatedResult with entries centered around value (including placeholder).
        """
        # nil UUID for placeholder
        nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
        now = datetime.now(UTC)

        # Determine is_test for placeholder and query filtering
        test_filter = is_test if is_test is not None else False

        # Create placeholder entry
        placeholder = RunEntry(
            id=RunEntryID(nil_uuid),
            board_id=board_id,
            identity_id=IdentityID(nil_uuid),
            score_event_id=ScoreEventID(nil_uuid),
            primary_value=target_value,
            is_test=test_filter,
            is_placeholder=True,
            created_at=now,
            updated_at=now,
        )

        # Compute placeholder's hypothetical rank
        placeholder_rank = await self._get_value_rank(target_value, board_id, sort_fields, is_test)
        placeholder.rank = placeholder_rank

        # Calculate window sizes
        ideal_above_count = limit // 2
        ideal_below_count = limit - ideal_above_count - 1
        max_side_items = limit - 1

        # Build base query
        base_query = select(RunEntryORM).where(
            RunEntryORM.deleted_at.is_(None),
            RunEntryORM.board_id == board_id.uuid,
        )
        if is_test is not None:
            base_query = base_query.where(RunEntryORM.is_test == is_test)

        # Extract placeholder position values
        target_values = self._extract_target_values(placeholder, sort_fields)

        # Build "above" query (better ranked, closest first)
        above_clause = self._build_position_clause(target_values, sort_fields, before_target=True)
        above_query = base_query.where(above_clause)
        above_query = self._apply_sort(above_query, self._invert_sort_fields(sort_fields))
        above_query = above_query.limit(max_side_items + 1)

        # Build "below" query (worse ranked, closest first)
        # For placeholder with newest timestamp, all same-value entries are "below"
        below_clause = self._build_position_clause_for_value(target_values, sort_fields)
        below_query = base_query.where(below_clause)
        below_query = self._apply_sort(below_query, sort_fields)
        below_query = below_query.limit(max_side_items + 1)

        # Execute both queries
        above_result = await self.session.execute(above_query)
        above_orms = list(above_result.scalars().all())

        below_result = await self.session.execute(below_query)
        below_orms = list(below_result.scalars().all())

        # Adjust window sizes based on available items
        available_above = len(above_orms)
        available_below = len(below_orms)

        if available_above < ideal_above_count:
            actual_above_count = available_above
            actual_below_count = min(available_below, limit - 1 - actual_above_count)
        elif available_below < ideal_below_count:
            actual_below_count = available_below
            actual_above_count = min(available_above, limit - 1 - actual_below_count)
        else:
            actual_above_count = ideal_above_count
            actual_below_count = ideal_below_count

        # Determine pagination flags
        has_prev = available_above > actual_above_count
        has_next = available_below > actual_below_count

        # Trim to adjusted window sizes
        above_orms = above_orms[:actual_above_count]
        below_orms = below_orms[:actual_below_count]

        # Reverse above results (they were fetched closest-first, need best-first)
        above_orms.reverse()

        # Build results with computed ranks
        items: list[RunEntry] = []

        # Add above items with ranks
        for i, orm in enumerate(above_orms):
            entry = self._to_domain(orm)
            entry.rank = placeholder_rank - (actual_above_count - i)
            items.append(entry)

        # Add placeholder
        items.append(placeholder)

        # Add below items with ranks
        for i, orm in enumerate(below_orms):
            entry = self._to_domain(orm)
            entry.rank = placeholder_rank + i + 1
            items.append(entry)

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=None,
            prev_position=None,
        )

    async def _get_value_rank(
        self,
        value: float,
        board_id: BoardID,
        sort_fields: "list[SortField]",
        is_test: bool | None = None,
    ) -> int:
        """Compute hypothetical rank for a value using COUNT approach.

        Counts how many entries rank better than the given value.
        For a placeholder (newest timestamp), entries with the same value
        are counted as "below" since the placeholder would be at the top
        of any same-value group.

        Args:
            value: The score value to compute rank for.
            board_id: Board ID to filter by.
            sort_fields: Sort fields defining the ranking order.
            is_test: Optional filter for test entries.

        Returns:
            Rank (1-indexed, where 1 is the best).
        """
        # Get the primary sort field (should be "primary_value")
        primary_field = sort_fields[0]
        value_column = self._get_orm_column(primary_field.name)

        # For DESC: better means value > target
        # For ASC: better means value < target
        if primary_field.direction == PaginationSortDirection.DESC:
            better_condition = value_column > value
        else:
            better_condition = value_column < value

        # Count entries that rank better
        count_query = (
            select(func.count())
            .select_from(RunEntryORM)
            .where(RunEntryORM.deleted_at.is_(None))
            .where(RunEntryORM.board_id == board_id.uuid)
            .where(better_condition)
        )

        if is_test is not None:
            count_query = count_query.where(RunEntryORM.is_test == is_test)

        result = await self.session.execute(count_query)
        better_count = result.scalar_one()

        return better_count + 1

    def _build_position_clause_for_value(
        self,
        target_values: dict[str, Any],
        sort_fields: "list[SortField]",
    ) -> Any:
        """Build WHERE clause for rows after a hypothetical value position.

        For a placeholder with the newest timestamp, entries that rank "below" are:
        - Entries with worse value (according to sort direction)
        - Entries with same value (since placeholder has newest created_at)

        Args:
            target_values: Dict of sort field values from placeholder.
            sort_fields: List of sort fields.

        Returns:
            SQLAlchemy WHERE clause.
        """
        # Get the primary sort field (should be "primary_value")
        primary_field = sort_fields[0]
        value_column = self._get_orm_column(primary_field.name)
        target_value = target_values[primary_field.name]

        # For DESC: below means value <= target (same or worse)
        # For ASC: below means value >= target (same or worse)
        if primary_field.direction == PaginationSortDirection.DESC:
            return value_column <= target_value
        else:
            return value_column >= target_value


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
