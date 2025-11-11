"""Game repository services."""

from typing import Any

from pydantic import UUID4
from sqlalchemy import select

from leadr.common.repositories import BaseRepository
from leadr.games.adapters.orm import GameORM
from leadr.games.domain.game import Game


class GameRepository(BaseRepository[Game, GameORM]):
    """Game repository for managing game persistence."""

    def _to_domain(self, orm: GameORM) -> Game:
        """Convert ORM model to domain entity."""
        return Game(
            id=orm.id,
            account_id=orm.account_id,
            name=orm.name,
            steam_app_id=orm.steam_app_id,
            default_board_id=orm.default_board_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: Game) -> GameORM:
        """Convert domain entity to ORM model."""
        return GameORM(
            id=entity.id,
            account_id=entity.account_id,
            name=entity.name,
            steam_app_id=entity.steam_app_id,
            default_board_id=entity.default_board_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[GameORM]:
        """Get the ORM model class."""
        return GameORM

    async def filter(self, account_id: UUID4, **kwargs: Any) -> list[Game]:
        """Filter games by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of games for the account matching the filter criteria
        """
        query = select(GameORM).where(
            GameORM.account_id == account_id,
            GameORM.deleted_at.is_(None),
        )

        # Future: Add additional filters here as needed
        # if "name" in kwargs:
        #     query = query.where(GameORM.name == kwargs["name"])

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
