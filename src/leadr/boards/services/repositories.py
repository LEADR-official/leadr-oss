"""Board repository services."""

from typing import Any

from pydantic import UUID4
from sqlalchemy import select

from leadr.boards.adapters.orm import BoardORM
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.common.repositories import BaseRepository


class BoardRepository(BaseRepository[Board, BoardORM]):
    """Board repository for managing board persistence."""

    def _to_domain(self, orm: BoardORM) -> Board:
        """Convert ORM model to domain entity."""
        return Board(
            id=orm.id,
            account_id=orm.account_id,
            game_id=orm.game_id,
            name=orm.name,
            icon=orm.icon,
            short_code=orm.short_code,
            unit=orm.unit,
            is_active=orm.is_active,
            sort_direction=SortDirection(orm.sort_direction),
            keep_strategy=KeepStrategy(orm.keep_strategy),
            template_id=orm.template_id,
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
            id=entity.id,
            account_id=entity.account_id,
            game_id=entity.game_id,
            name=entity.name,
            icon=entity.icon,
            short_code=entity.short_code,
            unit=entity.unit,
            is_active=entity.is_active,
            sort_direction=entity.sort_direction.value,
            keep_strategy=entity.keep_strategy.value,
            template_id=entity.template_id,
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

    async def filter(self, account_id: UUID4, **kwargs: Any) -> list[Board]:
        """Filter boards by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of boards for the account matching the filter criteria
        """
        query = select(BoardORM).where(
            BoardORM.account_id == account_id,
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
