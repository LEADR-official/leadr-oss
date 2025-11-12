"""Score repository services."""

from typing import Any
from uuid import UUID

from pydantic import UUID4
from sqlalchemy import select

from leadr.common.repositories import BaseRepository
from leadr.scores.adapters.orm import ScoreORM
from leadr.scores.domain.score import Score


class ScoreRepository(BaseRepository[Score, ScoreORM]):
    """Score repository for managing score persistence."""

    def _to_domain(self, orm: ScoreORM) -> Score:
        """Convert ORM model to domain entity."""
        return Score(
            id=orm.id,
            account_id=orm.account_id,
            game_id=orm.game_id,
            board_id=orm.board_id,
            device_id=orm.device_id,
            player_name=orm.player_name,
            value=orm.value,
            value_display=orm.value_display,
            filter_timezone=orm.filter_timezone,
            filter_country=orm.filter_country,
            filter_city=orm.filter_city,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: Score) -> ScoreORM:
        """Convert domain entity to ORM model."""
        return ScoreORM(
            id=entity.id,
            account_id=entity.account_id,
            game_id=entity.game_id,
            board_id=entity.board_id,
            device_id=entity.device_id,
            player_name=entity.player_name,
            value=entity.value,
            value_display=entity.value_display,
            filter_timezone=entity.filter_timezone,
            filter_country=entity.filter_country,
            filter_city=entity.filter_city,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[ScoreORM]:
        """Get the ORM model class."""
        return ScoreORM

    async def filter(
        self,
        account_id: UUID4,
        board_id: UUID | None = None,
        game_id: UUID | None = None,
        device_id: UUID | None = None,
        **kwargs: Any,
    ) -> list[Score]:
        """Filter scores by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            device_id: Optional device ID to filter by
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of scores for the account matching the filter criteria
        """
        query = select(ScoreORM).where(
            ScoreORM.account_id == account_id,
            ScoreORM.deleted_at.is_(None),
        )

        # Apply optional filters
        if board_id is not None:
            query = query.where(ScoreORM.board_id == board_id)

        if game_id is not None:
            query = query.where(ScoreORM.game_id == game_id)

        if device_id is not None:
            query = query.where(ScoreORM.device_id == device_id)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
