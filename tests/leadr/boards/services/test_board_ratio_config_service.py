"""Tests for BoardRatioConfigService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    ZeroDenominatorPolicy,
)
from leadr.boards.services.board_ratio_config_service import BoardRatioConfigService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, BoardRatioConfigID


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock session."""
    return MagicMock()


@pytest.fixture
def service(mock_session: MagicMock) -> BoardRatioConfigService:
    """Create a BoardRatioConfigService with mock repository."""
    svc = BoardRatioConfigService(mock_session, repository=MagicMock())
    return svc


@pytest.mark.asyncio
class TestBoardRatioConfigService:
    """Test cases for BoardRatioConfigService."""

    async def test_create_ratio_config(self, service: BoardRatioConfigService) -> None:
        """Creating a ratio config succeeds."""
        # Arrange
        ratio_board_id = BoardID(uuid4())
        numerator_board_id = BoardID(uuid4())
        denominator_board_id = BoardID(uuid4())

        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Act
        config = await service.create_ratio_config(
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )

        # Assert
        assert config.board_id == ratio_board_id
        assert config.numerator_board_id == numerator_board_id
        assert config.denominator_board_id == denominator_board_id
        assert config.zero_denominator_policy == ZeroDenominatorPolicy.NULL
        assert config.display == RatioDisplay.RAW
        service.repository.create.assert_called_once()

    async def test_create_ratio_config_with_options(self, service: BoardRatioConfigService) -> None:
        """Creating a ratio config with custom options succeeds."""
        # Arrange
        ratio_board_id = BoardID(uuid4())
        numerator_board_id = BoardID(uuid4())
        denominator_board_id = BoardID(uuid4())

        service.repository.create = AsyncMock(side_effect=lambda e: e)

        # Act
        config = await service.create_ratio_config(
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
            zero_denominator_policy=ZeroDenominatorPolicy.INFINITY,
            min_denominator=1,
            display=RatioDisplay.PERCENT,
            decimals=1,
        )

        # Assert
        assert config.zero_denominator_policy == ZeroDenominatorPolicy.INFINITY
        assert config.min_denominator == 1
        assert config.display == RatioDisplay.PERCENT
        assert config.decimals == 1
        service.repository.create.assert_called_once()

    async def test_get_ratio_config(self, service: BoardRatioConfigService) -> None:
        """Getting a ratio config by ID succeeds."""
        # Arrange
        config_id = BoardRatioConfigID()
        ratio_board_id = BoardID(uuid4())
        numerator_board_id = BoardID(uuid4())
        denominator_board_id = BoardID(uuid4())

        expected_config = BoardRatioConfig(
            id=config_id,
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_config)

        # Act
        retrieved = await service.get_ratio_config(config_id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == config_id
        service.repository.get_by_id.assert_called_once_with(config_id.uuid)

    async def test_get_ratio_config_not_found(self, service: BoardRatioConfigService) -> None:
        """Getting a non-existent ratio config returns None."""
        # Arrange
        config_id = BoardRatioConfigID()
        service.repository.get_by_id = AsyncMock(return_value=None)

        # Act
        result = await service.get_ratio_config(config_id)

        # Assert
        assert result is None
        service.repository.get_by_id.assert_called_once_with(config_id.uuid)

    async def test_get_by_id_or_raise_success(self, service: BoardRatioConfigService) -> None:
        """get_by_id_or_raise returns config when found."""
        # Arrange
        config_id = BoardRatioConfigID()
        ratio_board_id = BoardID(uuid4())
        numerator_board_id = BoardID(uuid4())
        denominator_board_id = BoardID(uuid4())

        expected_config = BoardRatioConfig(
            id=config_id,
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )

        service.repository.get_by_id = AsyncMock(return_value=expected_config)

        # Act
        result = await service.get_by_id_or_raise(config_id)

        # Assert
        assert result.id == config_id
        service.repository.get_by_id.assert_called_once_with(config_id.uuid)

    async def test_get_by_id_or_raise_not_found(self, service: BoardRatioConfigService) -> None:
        """get_by_id_or_raise raises when not found."""
        # Arrange
        config_id = BoardRatioConfigID()
        service.repository.get_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(EntityNotFoundError):
            await service.get_by_id_or_raise(config_id)

        service.repository.get_by_id.assert_called_once_with(config_id.uuid)

    async def test_get_by_board_id(self, service: BoardRatioConfigService) -> None:
        """Getting a ratio config by board ID succeeds."""
        # Arrange
        config_id = BoardRatioConfigID()
        ratio_board_id = BoardID(uuid4())
        numerator_board_id = BoardID(uuid4())
        denominator_board_id = BoardID(uuid4())

        expected_config = BoardRatioConfig(
            id=config_id,
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )

        service.repository.get_by_board_id = AsyncMock(return_value=expected_config)

        # Act
        retrieved = await service.get_by_board_id(ratio_board_id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == config_id
        service.repository.get_by_board_id.assert_called_once_with(ratio_board_id.uuid)

    async def test_get_by_board_id_not_found(self, service: BoardRatioConfigService) -> None:
        """Getting ratio config by non-existent board ID returns None."""
        # Arrange
        board_id = BoardID()
        service.repository.get_by_board_id = AsyncMock(return_value=None)

        # Act
        result = await service.get_by_board_id(board_id)

        # Assert
        assert result is None
        service.repository.get_by_board_id.assert_called_once_with(board_id.uuid)

    async def test_update_ratio_config(self, service: BoardRatioConfigService) -> None:
        """Updating a ratio config succeeds."""
        # Arrange
        config_id = BoardRatioConfigID()
        ratio_board_id = BoardID(uuid4())
        numerator_board_id = BoardID(uuid4())
        denominator_board_id = BoardID(uuid4())

        existing_config = BoardRatioConfig(
            id=config_id,
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )

        service.repository.get_by_id = AsyncMock(return_value=existing_config)
        service.repository.update = AsyncMock(side_effect=lambda e: e)

        # Act
        updated = await service.update_ratio_config(
            config_id=config_id,
            min_denominator=10,
            display=RatioDisplay.PERCENT,
        )

        # Assert
        assert updated.min_denominator == 10
        assert updated.display == RatioDisplay.PERCENT
        service.repository.get_by_id.assert_called_once_with(config_id.uuid)
        service.repository.update.assert_called_once()

    async def test_soft_delete(self, service: BoardRatioConfigService) -> None:
        """Soft deleting a ratio config succeeds."""
        # Arrange
        config_id = BoardRatioConfigID()
        ratio_board_id = BoardID(uuid4())
        numerator_board_id = BoardID(uuid4())
        denominator_board_id = BoardID(uuid4())

        existing_config = BoardRatioConfig(
            id=config_id,
            board_id=ratio_board_id,
            numerator_board_id=numerator_board_id,
            denominator_board_id=denominator_board_id,
        )

        service.repository.get_by_id = AsyncMock(return_value=existing_config)
        service.repository.delete = AsyncMock()

        # Act
        deleted = await service.soft_delete(config_id)

        # Assert
        assert deleted.id == config_id
        service.repository.get_by_id.assert_called_once_with(config_id.uuid)
        service.repository.delete.assert_called_once_with(config_id.uuid)
