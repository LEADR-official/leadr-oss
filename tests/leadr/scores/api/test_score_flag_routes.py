"""Tests for Score Flag API routes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.account_service import AccountService
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.ids import AccountID
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import (
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.services.anti_cheat_repositories import ScoreFlagRepository
from leadr.scores.services.score_event_service import ScoreEventService


@pytest.mark.asyncio
class TestScoreFlagRoutes:
    """Test suite for Score Flag API routes."""

    async def test_list_flags(self, client: AsyncClient, db_session, test_api_key):
        """Test listing score flags via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_123",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score events
        event_service = ScoreEventService(db_session)
        event1 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )
        event2 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 200.0},
        )

        # Create flags for the score events
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "duplicate submission detected"},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # List flags
        response = await client.get(
            f"/score-flags?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        flag_types = {f["flag_type"] for f in data["data"]}
        assert "velocity" in flag_types
        assert "duplicate" in flag_types

    async def test_list_flags_filter_by_board(self, client: AsyncClient, db_session, test_api_key):
        """Test filtering flags by board_id via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_456",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 1",
            icon="trophy",
            short_code="B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 2",
            icon="star",
            short_code="B2",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score events for both boards
        event_service = ScoreEventService(db_session)
        event1 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )
        event2 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board2.id,
            identity_id=identity.id,
            event_payload={"value": 200.0},
        )

        # Create flags for both score events
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"board": "board1"},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={"board": "board2"},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Filter by board1
        response = await client.get(
            f"/score-flags?account_id={account.id}&board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["flag_type"] == "velocity"

    async def test_list_flags_filter_by_status(self, client: AsyncClient, db_session, test_api_key):
        """Test filtering flags by status via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_789",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score events
        event_service = ScoreEventService(db_session)
        event1 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )
        event2 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 200.0},
        )

        # Create flags with different statuses
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={},
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Filter by pending status
        response = await client.get(
            f"/score-flags?account_id={account.id}&status=pending",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["status"] == "pending"
        assert data["data"][0]["flag_type"] == "velocity"

    async def test_list_flags_filter_by_flag_type(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering flags by flag_type via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_aaa",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score events
        event_service = ScoreEventService(db_session)
        event1 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )
        event2 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 200.0},
        )

        # Create flags with different types
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Filter by velocity type
        response = await client.get(
            f"/score-flags?account_id={account.id}&flag_type=velocity",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["flag_type"] == "velocity"

    async def test_get_flag(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single score flag by ID via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_bbb",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Get flag
        response = await client.get(
            f"/score-flags/{created_flag.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(created_flag.id)
        assert data["flag_type"] == "velocity"
        assert data["confidence"] == "medium"
        assert data["status"] == "pending"
        assert data["metadata"]["reason"] == "score improved too quickly"

    async def test_get_flag_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent flag returns 404."""
        response = await client.get(
            "/score-flags/flg_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_review_flag(self, client: AsyncClient, db_session, test_api_key):
        """Test reviewing a score flag via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_ccc",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Review flag - mark as confirmed cheat
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={
                "status": "confirmed_cheat",
                "reviewer_decision": "Verified cheating behavior",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed_cheat"
        assert data["reviewer_decision"] == "Verified cheating behavior"
        assert data["reviewed_at"] is not None

    async def test_review_flag_as_false_positive(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test marking a flag as false positive via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_ddd",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Review flag - mark as false positive
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={
                "status": "false_positive",
                "reviewer_decision": "Legitimate gameplay",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "false_positive"
        assert data["reviewer_decision"] == "Legitimate gameplay"

    async def test_soft_delete_flag(self, client: AsyncClient, db_session, test_api_key):
        """Test soft-deleting a score flag via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_eee",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Soft-delete flag
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200

        # Verify it's not in list
        response = await client.get(
            f"/score-flags?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        assert len(response.json()["data"]) == 0

    async def test_list_flags_excludes_deleted(self, client: AsyncClient, db_session, test_api_key):
        """Test that list_flags excludes soft-deleted flags."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_fff",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create two flags
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag1 = await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Soft-delete flag1 directly via repository
        flag1_entity = await flag_repo.get_by_id(created_flag1.id)
        assert flag1_entity is not None
        flag1_entity.deleted_at = datetime.now(UTC)
        await flag_repo.update(flag1_entity)

        # List should only return flag2
        response = await client.get(
            f"/score-flags?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["flag_type"] == "duplicate"

    async def test_superadmin_list_score_flags_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list score flags WITHOUT account_id and sees all."""

        # Create two accounts with score flags in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Flags",
            slug="account-one-flags",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Flags",
            slug="account-two-flags",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games, identities, boards and score events for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game Flag 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Flag 2",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account1.id,
            game_id=game1.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_superadmin_test_1",
            display_name="Player1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account2.id,
            game_id=game2.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_superadmin_test_2",
            display_name="Player2",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Board Flag 1",
            icon="trophy",
            short_code="BFL1A1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Board Flag 2",
            icon="star",
            short_code="BFL2A2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event1 = await event_service.create_score_event(
            account_id=account1.id,
            game_id=game1.id,
            board_id=board1.id,
            identity_id=identity1.id,
            event_payload={"value": 1000.0},
        )
        event2 = await event_service.create_score_event(
            account_id=account2.id,
            game_id=game2.id,
            board_id=board2.id,
            identity_id=identity2.id,
            event_payload={"value": 2000.0},
        )

        # Create flags for each score event
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"source": "account1"},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={"source": "account2"},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # List score flags WITHOUT account_id - should return flags from ALL accounts
        response = await authenticated_client.get("/score-flags")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain flags from both accounts
        flag_types = {f["flag_type"] for f in data["data"]}
        assert "velocity" in flag_types
        assert "duplicate" in flag_types

    async def test_list_flags_filter_by_game(self, client: AsyncClient, db_session, test_api_key):
        """Test filtering flags by game_id via API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account.id,
            name="Game 2",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game1.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_game1",
            display_name="TestPlayer",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game2.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_game2",
            display_name="TestPlayer2",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game1.id,
            name="Board 1",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game2.id,
            name="Board 2",
            icon="star",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score events for both games
        event_service = ScoreEventService(db_session)
        event1 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game1.id,
            board_id=board1.id,
            identity_id=identity1.id,
            event_payload={"value": 100.0},
        )
        event2 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game2.id,
            board_id=board2.id,
            identity_id=identity2.id,
            event_payload={"value": 200.0},
        )

        # Create flags for both score events
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"game": "game1"},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={"game": "game2"},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Filter by game1
        response = await client.get(
            f"/score-flags?account_id={account.id}&game_id={game1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["flag_type"] == "velocity"

    async def test_list_flags_invalid_cursor(self, client: AsyncClient, db_session, test_api_key):
        """Test listing flags with invalid cursor returns 400."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.get(
            f"/score-flags?account_id={account.id}&cursor=invalid_cursor_here",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400

    async def test_update_flag_invalid_status(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a flag with invalid status returns 422 (Pydantic validation)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_invalid_status",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Try to update with invalid status
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={"status": "invalid_status"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 422  # Pydantic validation error

    async def test_update_flag_no_data(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a flag without providing any data returns 400."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_no_data",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Try to update without any data
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert (
            "Must provide either status, reviewer_decision, or deleted=true"
            in response.json()["error"]
        )

    async def test_update_flag_reviewer_decision_only(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test updating a flag with only reviewer_decision (no status change)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_decision_only",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Update only reviewer_decision
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={"reviewer_decision": "Needs more investigation"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reviewer_decision"] == "Needs more investigation"
        assert data["status"] == "pending"  # Status unchanged

    async def test_create_flag_success(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a score flag via API with default values."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_create_flag",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score event
        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create flag via API with defaults
        response = await client.post(
            "/score-flags",
            json={"score_event_id": str(event.id)},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["score_event_id"] == str(event.id)
        assert data["flag_type"] == "manual"
        assert data["confidence"] == "medium"
        assert data["status"] == "removed"  # Default for manual admin flagging
        assert data["metadata"] == {}

    async def test_create_flag_with_custom_type(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score flag with a custom flag type (e.g., duplicate)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_create_custom",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TC2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create flag with custom type and metadata
        response = await client.post(
            "/score-flags",
            json={
                "score_event_id": str(event.id),
                "flag_type": "duplicate",
                "confidence": "high",
                "metadata": {"reason": "Manually flagged as duplicate"},
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["flag_type"] == "duplicate"
        assert data["confidence"] == "high"
        assert data["metadata"]["reason"] == "Manually flagged as duplicate"

    async def test_create_flag_with_custom_status(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score flag with a custom status (e.g., pending)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_custom_status",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TS2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        # Create flag with explicit pending status (overriding default of removed)
        response = await client.post(
            "/score-flags",
            json={
                "score_event_id": str(event.id),
                "status": "pending",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    async def test_create_flag_score_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a flag for non-existent score event returns 404."""
        fake_event_id = "sev_00000000-0000-0000-0000-000000000000"

        response = await client.post(
            "/score-flags",
            json={"score_event_id": fake_event_id},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "Score event not found" in response.json()["error"]

    async def test_create_flag_invalid_flag_type(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a flag with invalid flag_type returns 422 (Pydantic validation)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_invalid_type",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TI2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        response = await client.post(
            "/score-flags",
            json={
                "score_event_id": str(event.id),
                "flag_type": "invalid_type",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 422  # Pydantic validation error

    async def test_create_flag_invalid_confidence(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a flag with invalid confidence returns 422 (Pydantic validation)."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_invalid_conf",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TIC2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 100.0},
        )

        response = await client.post(
            "/score-flags",
            json={
                "score_event_id": str(event.id),
                "confidence": "invalid_confidence",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 422  # Pydantic validation error
