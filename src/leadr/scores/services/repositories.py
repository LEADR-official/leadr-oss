"""Score repository services."""

from typing import Any

from pydantic import UUID4
from sqlalchemy import select

from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, PrefixedID, ScoreID
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

    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        device_id: DeviceID | None = None,
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

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering scores")
        account_uuid = self._extract_uuid(account_id)
        query = select(ScoreORM).where(
            ScoreORM.account_id == account_uuid,
            ScoreORM.deleted_at.is_(None),
        )

        # Apply optional filters
        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(ScoreORM.board_id == board_uuid)

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(ScoreORM.game_id == game_uuid)

        if device_id is not None:
            device_uuid = self._extract_uuid(device_id)
            query = query.where(ScoreORM.device_id == device_uuid)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
