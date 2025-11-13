"""Game repository services."""

from typing import Any

from pydantic import UUID4
from sqlalchemy import select

from leadr.common.domain.ids import AccountID, BoardID, GameID, PrefixedID
from leadr.common.repositories import BaseRepository
from leadr.games.adapters.orm import GameORM
from leadr.games.domain.game import Game


class GameRepository(BaseRepository[Game, GameORM]):
    """Game repository for managing game persistence."""

    def _to_domain(self, orm: GameORM) -> Game:
        """Convert ORM model to domain entity."""
        return Game(
            id=GameID(orm.id),
            account_id=AccountID(orm.account_id),
            name=orm.name,
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

    async def filter(
        self, account_id: UUID4 | PrefixedID | None = None, **kwargs: Any
    ) -> list[Game]:
        """Filter games by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of games for the account matching the filter criteria

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering games")
        account_uuid = self._extract_uuid(account_id)
        query = select(GameORM).where(
            GameORM.account_id == account_uuid,
            GameORM.deleted_at.is_(None),
        )

        # Future: Add additional filters here as needed
        # if "name" in kwargs:
        #     query = query.where(GameORM.name == kwargs["name"])

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
