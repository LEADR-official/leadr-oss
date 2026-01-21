"""Score repository services."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.common.domain.pagination import SortDirection, SortField
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository
from leadr.scores.adapters.orm import ScoreORM, ScoreStatusEnum
from leadr.scores.domain.anti_cheat.enums import ScoreStatus
from leadr.scores.domain.score import Score

if TYPE_CHECKING:
    from leadr.boards.domain.board import Board

# Sentinel nil UUID for placeholder scores
NIL_UUID = UUID("00000000-0000-0000-0000-000000000000")


class ScoreRepository(BaseRepository[Score, ScoreORM]):
    """Score repository for managing score persistence."""

    def _to_domain(self, orm: ScoreORM, rank: int | None = None) -> Score:
        """Convert ORM model to domain entity.

        Args:
            orm: ScoreORM model instance
            rank: Optional rank value computed from query (1-indexed)

        Returns:
            Score domain entity with optional rank populated
        """
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
            rank=rank,
            is_test=orm.is_test,
            status=ScoreStatus(orm.status.value),
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
            is_test=entity.is_test,
            status=ScoreStatusEnum(entity.status.value),
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
        include_all_statuses: bool = False,
    ) -> Score | None:
        """Get the active score for a specific device on a board.

        This is an optimized single-record lookup for keep_strategy logic.

        Args:
            account_id: Account ID to filter by (multi-tenant safety).
            device_id: Device ID to search for.
            board_id: Board ID to search for.
            include_all_statuses: If True, includes all statuses. Default excludes
                REJECTED and PROVISIONAL scores.

        Returns:
            The first matching Score or None if no score exists.
        """
        query = (
            select(ScoreORM)
            .where(ScoreORM.deleted_at.is_(None))
            .where(ScoreORM.account_id == self._extract_uuid(account_id))
            .where(ScoreORM.device_id == self._extract_uuid(device_id))
            .where(ScoreORM.board_id == self._extract_uuid(board_id))
        )

        if not include_all_statuses:
            query = query.where(ScoreORM.status.notin_(self.EXCLUDED_STATUSES))

        query = query.limit(1)
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

    # Excluded statuses for default queries (rejected and provisional scores hidden)
    EXCLUDED_STATUSES = [ScoreStatus.REJECTED.value, ScoreStatus.PROVISIONAL.value]

    async def filter(
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        device_id: DeviceID | None = None,
        is_test: bool | None = None,
        status: ScoreStatus | None = None,
        include_all_statuses: bool = False,
        *,
        pagination: PaginationParams,
        around_score: Score | None = None,
        around_score_value: float | None = None,
        around_value_board: "Board | None" = None,
        **kwargs: Any,
    ) -> PaginatedResult[Score]:
        """Filter scores by account and optional criteria.

        Args:
            account_id: Optional account ID to filter by. If None, returns all scores
                (superadmin use case). Regular users should always pass account_id.
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            device_id: Optional device ID to filter by
            is_test: Optional filter for test scores. True returns only test scores,
                False returns only production scores, None returns all scores.
            status: Optional filter for specific score status. If None, excludes
                REJECTED and PROVISIONAL scores by default.
            include_all_statuses: If True, includes all statuses (admin use case).
                Overrides the default exclusion of REJECTED and PROVISIONAL.
            pagination: Pagination parameters (required)
            around_score: Optional target score to center results around. When provided,
                returns a window of scores centered on this score (mutually exclusive
                with cursor pagination).
            around_score_value: Optional value to center results around. Returns a
                placeholder score with is_placeholder=True at the appropriate position.
            around_value_board: The board entity (required when around_score_value is set).
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing scores

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        # Build base query - exclude deleted and (by default) rejected/provisional scores
        query = select(ScoreORM).where(ScoreORM.deleted_at.is_(None))

        # Apply status filtering
        if status is not None:
            # Filter for specific status
            query = query.where(ScoreORM.status == status.value)
        elif not include_all_statuses:
            # Default: exclude REJECTED and PROVISIONAL
            query = query.where(ScoreORM.status.notin_(self.EXCLUDED_STATUSES))

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

        if is_test is not None:
            query = query.where(ScoreORM.is_test == is_test)
            filters_dict["is_test"] = str(is_test)

        # Validate sort fields
        for sort_field in pagination.sort_spec:
            if sort_field.name not in self.SORTABLE_FIELDS:
                raise ValueError(
                    f"Unknown sort field: {sort_field.name}. "
                    f"Valid fields: {', '.join(sorted(self.SORTABLE_FIELDS))}"
                )

        # Branch: around_score query vs around_score_value vs normal cursor pagination
        # Note: around_score/around_score_value require board_id (validated at route level),
        # so rank is always computed
        if around_score is not None:
            return await self._execute_around_query(
                base_query=query,
                target_score=around_score,
                sort_fields=pagination.sort_spec,
                limit=pagination.limit,
            )

        if around_score_value is not None and around_value_board is not None:
            return await self._execute_around_value_query(
                base_query=query,
                value=around_score_value,
                board=around_value_board,
                sort_fields=pagination.sort_spec,
                limit=pagination.limit,
                is_test=is_test,
            )

        # Handle cursor if present
        cursor = None
        if pagination.has_cursor():
            cursor = pagination.decode_cursor()
            # Validate cursor state matches current query
            if cursor is not None:
                cursor.validate_state(pagination.sort_spec, filters_dict)

        # Execute paginated query with optional rank computation
        if board_id is not None:
            return await self._execute_ranked_paginated_query(
                query=query,
                sort_fields=pagination.sort_spec,
                cursor=cursor,
                limit=pagination.limit,
            )

        # Execute standard paginated query (no rank)
        return await self._execute_paginated_query(
            query=query,
            sort_fields=pagination.sort_spec,
            cursor=cursor,
            limit=pagination.limit,
        )

    async def _execute_around_query(
        self,
        base_query: Select[tuple[ScoreORM]],
        target_score: Score,
        sort_fields: list[SortField],
        limit: int,
    ) -> PaginatedResult[Score]:
        """Execute a query that returns scores centered around a target score with ranks.

        This method fetches scores in a window around the target score, respecting
        the sort order. For example, with limit=5 and a DESC value sort, it returns
        2 scores above (better ranked), the target, and 2 scores below (worse ranked).

        When the target is near an edge (top or bottom of the leaderboard), the window
        adjusts: if there aren't enough scores on one side, more are fetched from the
        other side to fill up to the limit.

        Note: This method always computes ranks because around_score requires board_id
        (validated at route level).

        Args:
            base_query: SQLAlchemy query with all filters applied (account, board, etc.)
            target_score: The score to center results around
            sort_fields: List of sort fields defining the ranking order
            limit: Total number of scores to return (including target)

        Returns:
            PaginatedResult with scores (including ranks) centered around target
        """
        # Compute target score's rank first
        target_rank = await self.get_score_rank(target_score, sort_fields)

        # Calculate initial window sizes (ideal split)
        ideal_above_count = limit // 2
        ideal_below_count = limit - ideal_above_count - 1
        max_side_items = limit - 1  # Max items from one side (excluding target)

        # Extract target position values for all sort fields
        target_values = self._extract_target_values(target_score, sort_fields)

        # Build "above" query (scores ranked better than target, closest first)
        # Fetch more than needed to allow compensation when below is short
        above_query = self._build_around_subquery(
            base_query=base_query,
            target_values=target_values,
            sort_fields=sort_fields,
            direction="above",
            limit=max_side_items + 1,  # +1 to detect has_prev
        )

        # Build "below" query (scores ranked worse than target, closest first)
        # Fetch more than needed to allow compensation when above is short
        below_query = self._build_around_subquery(
            base_query=base_query,
            target_values=target_values,
            sort_fields=sort_fields,
            direction="below",
            limit=max_side_items + 1,  # +1 to detect has_next
        )

        # Execute both queries
        above_result = await self.session.execute(above_query)
        above_orms = list(above_result.scalars().all())

        below_result = await self.session.execute(below_query)
        below_orms = list(below_result.scalars().all())

        # Adjust window sizes based on available items
        # If one side is short, give more slots to the other side
        available_above = len(above_orms)
        available_below = len(below_orms)

        if available_above < ideal_above_count:
            # Not enough above, give extra slots to below
            actual_above_count = available_above
            actual_below_count = min(available_below, limit - 1 - actual_above_count)
        elif available_below < ideal_below_count:
            # Not enough below, give extra slots to above
            actual_below_count = available_below
            actual_above_count = min(available_above, limit - 1 - actual_below_count)
        else:
            # Both sides have enough, use ideal split
            actual_above_count = ideal_above_count
            actual_below_count = ideal_below_count

        # Determine pagination flags (there's more beyond what we're showing)
        has_prev = available_above > actual_above_count
        has_next = available_below > actual_below_count

        # Trim to adjusted window sizes
        above_orms = above_orms[:actual_above_count]
        below_orms = below_orms[:actual_below_count]

        # Reverse above results (they were fetched closest-first, need best-first)
        above_orms.reverse()

        # Fetch target score ORM to include in results
        target_orm = await self._get_target_orm(target_score)

        # Build results with computed ranks
        # Ranks for "above" items: target_rank - actual_above_count, ..., target_rank - 1
        items: list[Score] = []
        for i, orm in enumerate(above_orms):
            rank = target_rank - (actual_above_count - i)
            items.append(self._to_domain(orm, rank=rank))

        if target_orm:
            items.append(self._to_domain(target_orm, rank=target_rank))

        # Ranks for "below" items: target_rank + 1, target_rank + 2, ...
        for i, orm in enumerate(below_orms):
            rank = target_rank + i + 1
            items.append(self._to_domain(orm, rank=rank))

        # Combine ORMs for cursor extraction
        all_orms: list[ScoreORM] = above_orms + ([target_orm] if target_orm else []) + below_orms

        # Build cursor positions for pagination
        prev_position = None
        next_position = None

        if all_orms and has_prev:
            prev_position = self._extract_cursor_position(all_orms[0], sort_fields)
        if all_orms and has_next:
            next_position = self._extract_cursor_position(all_orms[-1], sort_fields)

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=next_position,
            prev_position=prev_position,
        )

    async def _execute_around_value_query(
        self,
        base_query: Select[tuple[ScoreORM]],
        value: float,
        board: "Board",
        sort_fields: list[SortField],
        limit: int,
        is_test: bool | None = None,
    ) -> PaginatedResult[Score]:
        """Execute a query that returns scores centered around a hypothetical value.

        Creates a synthetic placeholder score with the given value and returns it
        along with neighboring scores. The placeholder has is_placeholder=True and
        uses sentinel nil UUIDs for id and device_id.

        Args:
            base_query: SQLAlchemy query with all filters applied (account, board, etc.)
            value: The hypothetical score value to center results around
            board: The board entity (for deriving account_id, game_id)
            sort_fields: List of sort fields defining the ranking order
            limit: Total number of scores to return (including placeholder)
            is_test: Optional filter for test scores. True for test pool ranking,
                False for production pool, None for all scores.

        Returns:
            PaginatedResult with scores (including placeholder) centered around value
        """
        # Create placeholder score with sentinel IDs
        now = datetime.now(UTC)
        placeholder = Score(
            id=ScoreID(NIL_UUID),
            account_id=board.account_id,
            game_id=board.game_id,
            board_id=board.id,
            device_id=DeviceID(NIL_UUID),
            player_name="",  # Empty for placeholder
            value=value,
            is_placeholder=True,
            is_test=is_test if is_test is not None else False,
            created_at=now,
            updated_at=now,
        )

        # Extract placeholder position values for sort field comparison
        target_values = self._extract_target_values(placeholder, sort_fields)

        # Compute placeholder's hypothetical rank (within test/production pool if specified)
        placeholder_rank = await self._get_value_rank(value, board.id, sort_fields, is_test)

        # Calculate window sizes (ideal split)
        ideal_above_count = limit // 2
        ideal_below_count = limit - ideal_above_count - 1
        max_side_items = limit - 1  # Max items from one side (excluding placeholder)

        # Build "above" query (scores ranked better than placeholder, closest first)
        above_query = self._build_around_subquery(
            base_query=base_query,
            target_values=target_values,
            sort_fields=sort_fields,
            direction="above",
            limit=max_side_items + 1,  # +1 to detect has_prev
        )

        # Build "below" query (scores ranked worse than placeholder, closest first)
        # For tie-breaking, placeholder is "newest" so same-value scores go below
        below_query = self._build_around_value_below_subquery(
            base_query=base_query,
            target_values=target_values,
            sort_fields=sort_fields,
            limit=max_side_items + 1,  # +1 to detect has_next
        )

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
        items: list[Score] = []

        # Add above items with ranks
        for i, orm in enumerate(above_orms):
            rank = placeholder_rank - (actual_above_count - i)
            items.append(self._to_domain(orm, rank=rank))

        # Add placeholder
        placeholder.rank = placeholder_rank
        items.append(placeholder)

        # Add below items with ranks
        for i, orm in enumerate(below_orms):
            rank = placeholder_rank + i + 1
            items.append(self._to_domain(orm, rank=rank))

        # Build cursor positions for pagination (using real scores, not placeholder)
        prev_position = None
        next_position = None

        if above_orms and has_prev:
            prev_position = self._extract_cursor_position(above_orms[0], sort_fields)
        if below_orms and has_next:
            next_position = self._extract_cursor_position(below_orms[-1], sort_fields)

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=next_position,
            prev_position=prev_position,
        )

    def _build_around_value_below_subquery(
        self,
        base_query: Select[tuple[ScoreORM]],
        target_values: dict[str, Any],
        sort_fields: list[SortField],
        limit: int,
    ) -> Select[tuple[ScoreORM]]:
        """Build subquery for scores below a hypothetical value.

        For "below" with a placeholder (newest timestamp), scores with the same value
        are considered "below" because the placeholder would be at the top of same-value
        scores due to having the newest created_at.

        Args:
            base_query: Base query with all filters applied
            target_values: Dict of sort field values from placeholder
            sort_fields: List of sort fields defining the ranking order
            limit: Maximum number of results

        Returns:
            SQLAlchemy query for scores that would rank below the value
        """
        # Build WHERE clause for scores worse than or equal to placeholder value
        # but excluding the exact same position (which would be the placeholder itself)
        # Since placeholder has newest timestamp, all same-value scores are "below"
        position_clause = self._build_position_clause_for_value(
            target_values=target_values,
            sort_fields=sort_fields,
        )

        query = base_query.where(position_clause)

        # Apply normal sort (closest to placeholder first)
        query = self._apply_sort(query, sort_fields)
        query = query.limit(limit)

        return query

    def _build_position_clause_for_value(
        self,
        target_values: dict[str, Any],
        sort_fields: list[SortField],
    ) -> Any:
        """Build WHERE clause for rows after a hypothetical value position.

        For a placeholder with the newest timestamp, scores that rank "below" are:
        - Scores with worse value (according to sort direction)
        - Scores with same value (since placeholder has newest created_at)

        This uses a simplified comparison on just the value field since the placeholder
        is assumed to be at the top of any same-value group.

        Args:
            target_values: Dict of sort field values from placeholder
            sort_fields: List of sort fields

        Returns:
            SQLAlchemy WHERE clause
        """
        # Get the primary sort field (should be "value")
        primary_field = sort_fields[0]
        value_column = self._get_orm_column(primary_field.name)
        target_value = target_values[primary_field.name]

        # For DESC: below means value <= target (same or worse)
        # For ASC: below means value >= target (same or worse)
        if primary_field.direction == SortDirection.DESC:
            return value_column <= target_value
        else:
            return value_column >= target_value

    async def _get_value_rank(
        self,
        value: float,
        board_id: BoardID,
        sort_fields: list[SortField],
        is_test: bool | None = None,
    ) -> int:
        """Compute hypothetical rank for a value using COUNT approach.

        Counts how many scores rank better than the given value.
        For a placeholder (newest timestamp), scores with the same value
        are counted as "below" since the placeholder would be at the top
        of any same-value group.

        Note: Ranks are computed separately for test vs production scores
        when is_test is specified.
        Rejected and provisional scores are excluded from rank calculations.

        Args:
            value: The score value to compute rank for
            board_id: Board ID to filter by
            sort_fields: Sort fields defining the ranking order
            is_test: Optional filter for test scores. True computes rank within
                test pool, False within production pool, None within all scores.

        Returns:
            Rank (1-indexed, where 1 is the best)
        """
        # Get the primary sort field (should be "value")
        primary_field = sort_fields[0]
        value_column = self._get_orm_column(primary_field.name)

        # For DESC: better means value > target
        # For ASC: better means value < target
        if primary_field.direction == SortDirection.DESC:
            better_condition = value_column > value
        else:
            better_condition = value_column < value

        # Count scores that rank better (within test/production pool if specified)
        # Exclude rejected and provisional scores from rank calculation
        count_query = (
            select(func.count())
            .select_from(ScoreORM)
            .where(ScoreORM.deleted_at.is_(None))
            .where(ScoreORM.status.notin_(self.EXCLUDED_STATUSES))
            .where(ScoreORM.board_id == self._extract_uuid(board_id))
            .where(better_condition)
        )

        if is_test is not None:
            count_query = count_query.where(ScoreORM.is_test == is_test)

        result = await self.session.execute(count_query)
        better_count = result.scalar_one()

        return better_count + 1  # Rank is 1-indexed

    def _extract_target_values(
        self,
        target_score: Score,
        sort_fields: list[SortField],
    ) -> dict[str, Any]:
        """Extract values from target score for each sort field.

        Args:
            target_score: The target score domain entity
            sort_fields: List of sort fields

        Returns:
            Dict mapping field names to their values from the target score
        """
        # Map ORM field names to domain entity attribute names
        field_mapping = {
            "filter_timezone": "timezone",
            "filter_country": "country",
            "filter_city": "city",
        }

        values = {}
        for sort_field in sort_fields:
            # Get the attribute name on the domain entity
            attr_name = field_mapping.get(sort_field.name, sort_field.name)
            value = getattr(target_score, attr_name)
            # For ID fields, extract the UUID
            if hasattr(value, "uuid"):
                value = value.uuid
            values[sort_field.name] = value
        return values

    def _build_around_subquery(
        self,
        base_query: Select[tuple[ScoreORM]],
        target_values: dict[str, Any],
        sort_fields: list[SortField],
        direction: str,
        limit: int,
    ) -> Select[tuple[ScoreORM]]:
        """Build a subquery for scores above or below the target.

        For "above" (better ranked): find scores that come BEFORE target in sort order,
        ordered by inverted sort (closest to target first).

        For "below" (worse ranked): find scores that come AFTER target in sort order,
        ordered by normal sort (closest to target first).

        Args:
            base_query: Base query with all filters applied
            target_values: Dict of sort field values from target score
            sort_fields: List of sort fields defining the ranking order
            direction: "above" for better ranked, "below" for worse ranked
            limit: Maximum number of results

        Returns:
            SQLAlchemy query for the subquery
        """
        # Build WHERE clause for position comparison
        # "above" means rows that come BEFORE target in sort order
        # "below" means rows that come AFTER target in sort order
        position_clause = self._build_position_clause(
            target_values=target_values,
            sort_fields=sort_fields,
            before_target=(direction == "above"),
        )

        query = base_query.where(position_clause)

        # Apply sort order
        # For "above": use inverted sort to get closest to target first
        # For "below": use normal sort to get closest to target first
        if direction == "above":
            sort_fields_for_query = self._invert_sort_fields(sort_fields)
        else:
            sort_fields_for_query = sort_fields

        query = self._apply_sort(query, sort_fields_for_query)
        query = query.limit(limit)

        return query

    def _build_position_clause(
        self,
        target_values: dict[str, Any],
        sort_fields: list[SortField],
        before_target: bool,
    ) -> Any:
        """Build WHERE clause for rows before or after target position.

        This creates a compound comparison clause that respects the multi-field sort.
        For (value DESC, created_at DESC, id ASC) looking for rows BEFORE target:
        - value > target_value
        - OR (value = target_value AND created_at > target_created_at)
        - OR (value = target_value AND created_at = target_created_at AND id < target_id)

        Args:
            target_values: Dict of sort field values from target score
            sort_fields: List of sort fields
            before_target: True for rows before target (better ranked), False for after

        Returns:
            SQLAlchemy WHERE clause
        """
        or_conditions = []

        for i, sort_field in enumerate(sort_fields):
            # Determine comparison operator
            # For DESC: "before" means greater value, "after" means lesser value
            # For ASC: "before" means lesser value, "after" means greater value
            if before_target:
                if sort_field.direction == SortDirection.DESC:
                    comp_op = "__gt__"
                else:
                    comp_op = "__lt__"
            else:
                if sort_field.direction == SortDirection.DESC:
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

    def _invert_sort_fields(self, sort_fields: list[SortField]) -> list[SortField]:
        """Invert the direction of all sort fields.

        Args:
            sort_fields: Original sort fields

        Returns:
            New list with inverted sort directions
        """
        return [
            SortField(
                name=f.name,
                direction=SortDirection.ASC
                if f.direction == SortDirection.DESC
                else SortDirection.DESC,
            )
            for f in sort_fields
        ]

    async def _get_target_orm(self, target_score: Score) -> ScoreORM | None:
        """Fetch the ORM model for the target score.

        Args:
            target_score: Target score domain entity

        Returns:
            ScoreORM instance or None if not found
        """
        query = select(ScoreORM).where(
            ScoreORM.id == target_score.id.uuid,
            ScoreORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def _build_rank_order_by(self, sort_fields: list[SortField]) -> list[Any]:
        """Build ORDER BY expressions for ROW_NUMBER window function.

        Args:
            sort_fields: List of sort fields

        Returns:
            List of SQLAlchemy order_by expressions
        """
        order_by = []
        for sf in sort_fields:
            column = self._get_orm_column(sf.name)
            if sf.direction == SortDirection.DESC:
                order_by.append(column.desc())
            else:
                order_by.append(column.asc())
        return order_by

    async def _execute_ranked_paginated_query(
        self,
        query: Any,
        sort_fields: list[SortField],
        cursor: Any | None,
        limit: int,
    ) -> PaginatedResult[Score]:
        """Execute a paginated query with ROW_NUMBER rank computation.

        Uses a subquery with ROW_NUMBER() window function to compute global rank
        for each score, then applies cursor pagination on the results.

        Args:
            query: Base SQLAlchemy query with filters applied
            sort_fields: List of sort fields for ranking and sorting
            cursor: Optional pagination cursor
            limit: Number of items to return

        Returns:
            PaginatedResult with scores including computed ranks
        """
        from leadr.common.domain.pagination import PaginationDirection

        # Build ORDER BY for the window function
        rank_order = self._build_rank_order_by(sort_fields)

        # Create subquery with ROW_NUMBER
        rank_column = func.row_number().over(order_by=rank_order).label("rank")

        # Select all ScoreORM columns plus rank
        ranked_subquery = query.add_columns(rank_column).subquery()

        # Main query selects from the subquery
        main_query = select(ranked_subquery)

        # Apply cursor pagination on the rank column or sort columns
        if cursor is not None:
            cursor_where = self._build_ranked_cursor_where_clause(
                cursor, sort_fields, ranked_subquery
            )
            main_query = main_query.where(cursor_where)

        # Apply sorting to the main query
        for sf in sort_fields:
            col = ranked_subquery.c[sf.name]
            if sf.direction == SortDirection.DESC:
                main_query = main_query.order_by(col.desc())
            else:
                main_query = main_query.order_by(col.asc())

        # Fetch limit+1 to detect has_next
        main_query = main_query.limit(limit + 1)

        # Execute query
        result = await self.session.execute(main_query)
        rows = list(result.all())

        # Determine if there are more results
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        # Convert to domain entities with ranks
        items = []
        orms_for_cursor = []
        for row in rows:
            # row contains all columns from the subquery
            # Create a ScoreORM-like object from the row for _to_domain
            orm = self._row_to_orm(row)
            rank_value = row.rank
            items.append(self._to_domain(orm, rank=rank_value))
            orms_for_cursor.append(orm)

        # Determine pagination metadata
        if cursor is not None and cursor.direction == PaginationDirection.BACKWARD:
            has_next = True
            has_prev = has_more
            next_position = (
                self._extract_cursor_position(orms_for_cursor[-1], sort_fields)
                if orms_for_cursor
                else None
            )
            prev_position = (
                self._extract_cursor_position(orms_for_cursor[0], sort_fields)
                if orms_for_cursor and has_prev
                else None
            )
        else:
            has_next = has_more
            has_prev = cursor is not None
            next_position = (
                self._extract_cursor_position(orms_for_cursor[-1], sort_fields)
                if orms_for_cursor and has_next
                else None
            )
            prev_position = (
                self._extract_cursor_position(orms_for_cursor[0], sort_fields)
                if orms_for_cursor and has_prev
                else None
            )

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=next_position,
            prev_position=prev_position,
        )

    def _row_to_orm(self, row: Any) -> ScoreORM:
        """Convert a query result row to a ScoreORM-like object.

        Args:
            row: SQLAlchemy result row with all ScoreORM columns

        Returns:
            ScoreORM instance populated from the row
        """
        orm = ScoreORM()
        orm.id = row.id
        orm.account_id = row.account_id
        orm.game_id = row.game_id
        orm.board_id = row.board_id
        orm.device_id = row.device_id
        orm.player_name = row.player_name
        orm.value = row.value
        orm.value_display = row.value_display
        orm.filter_timezone = row.filter_timezone
        orm.filter_country = row.filter_country
        orm.filter_city = row.filter_city
        orm.score_metadata = row.score_metadata
        orm.is_test = row.is_test
        orm.status = row.status
        orm.created_at = row.created_at
        orm.updated_at = row.updated_at
        orm.deleted_at = row.deleted_at
        return orm

    def _build_ranked_cursor_where_clause(
        self,
        cursor: Any,
        sort_fields: list[SortField],
        subquery: Any,
    ) -> Any:
        """Build WHERE clause for cursor pagination on a ranked subquery.

        Args:
            cursor: Pagination cursor
            sort_fields: Sort fields
            subquery: The ranked subquery

        Returns:
            SQLAlchemy WHERE clause
        """
        from leadr.common.domain.pagination import PaginationDirection

        or_conditions = []
        position = cursor.position

        for i, sort_field in enumerate(sort_fields):
            # Determine comparison operator based on direction
            is_backward = cursor.direction == PaginationDirection.BACKWARD
            if sort_field.direction == SortDirection.DESC:
                comp_op = "__gt__" if is_backward else "__lt__"
            else:
                comp_op = "__lt__" if is_backward else "__gt__"

            # Build equality conditions for previous fields
            equality_conditions = []
            for j in range(i):
                prev_field = sort_fields[j]
                prev_column = subquery.c[prev_field.name]
                # Use ORM column for type conversion
                orm_column = self._get_orm_column(prev_field.name)
                prev_value = self._convert_cursor_value(position.values[j], orm_column)
                equality_conditions.append(prev_column == prev_value)

            # Add comparison for current field
            current_column = subquery.c[sort_field.name]
            # Use ORM column for type conversion
            orm_column = self._get_orm_column(sort_field.name)
            current_value = self._convert_cursor_value(position.values[i], orm_column)
            comparison = getattr(current_column, comp_op)(current_value)

            if equality_conditions:
                or_conditions.append(and_(*equality_conditions, comparison))
            else:
                or_conditions.append(comparison)

        return or_(*or_conditions)

    async def get_score_rank(
        self,
        score: Score,
        sort_fields: list[SortField],
    ) -> int:
        """Compute rank for a single score using COUNT approach.

        Counts how many scores rank better than the given score using the
        same multi-field comparison logic used for sorting.

        Note: Ranks are computed separately for test vs production scores.
        A test score's rank is within the test score pool only.
        Rejected and provisional scores are excluded from rank calculations.

        Args:
            score: Score to compute rank for
            sort_fields: Sort fields defining the ranking order

        Returns:
            Rank (1-indexed, where 1 is the best)
        """
        target_values = self._extract_target_values(score, sort_fields)

        # Build condition for "scores that rank better"
        # This is the same as "_build_position_clause" with before_target=True
        better_condition = self._build_position_clause(
            target_values=target_values,
            sort_fields=sort_fields,
            before_target=True,  # Scores that come BEFORE target = better ranked
        )

        # Count scores that rank better (within same test/production pool)
        # Exclude rejected and provisional scores from rank calculation
        count_query = (
            select(func.count())
            .select_from(ScoreORM)
            .where(ScoreORM.deleted_at.is_(None))
            .where(ScoreORM.status.notin_(self.EXCLUDED_STATUSES))
            .where(ScoreORM.board_id == score.board_id.uuid)
            .where(ScoreORM.is_test == score.is_test)
            .where(better_condition)
        )

        result = await self.session.execute(count_query)
        better_count = result.scalar_one()

        return better_count + 1  # Rank is 1-indexed
