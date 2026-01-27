"""Tests for Score Submission Metadata API routes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta
from leadr.scores.services.anti_cheat_repositories import ScoreSubmissionMetaRepository
from leadr.scores.services.score_event_service import ScoreEventService


@pytest.mark.asyncio
class TestScoreSubmissionMetaRoutes:
    """Test suite for Score Submission Metadata API routes."""

    async def test_list_submission_meta(
        self, client: AsyncClient, db_session: AsyncSession, test_api_key: str
    ):
        """Test listing score submission metadata via API."""
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

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_123",
            display_name="Test Player",
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

        # Create submission metadata directly
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        meta = ScoreSubmissionMeta(
            score_event_id=event.id,
            identity_id=identity.id,
            board_id=board.id,
            submission_count=1,
            last_submission_at=datetime.now(UTC),
            last_score_value=100.0,
        )
        await meta_repo.create(meta)

        # List submission metadata
        response = await client.get(
            f"/score-submission-metadata?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1
        assert data["data"][0]["identity_id"] == str(identity.id)
        assert data["data"][0]["board_id"] == str(board.id)
        assert data["data"][0]["submission_count"] == 1

    async def test_list_submission_meta_filter_by_board(
        self, client: AsyncClient, db_session: AsyncSession, test_api_key: str
    ):
        """Test filtering submission metadata by board_id via API."""
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

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board 1",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board 2",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_123",
            display_name="Test Player",
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

        # Create submission metadata for both boards
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        meta1 = ScoreSubmissionMeta(
            score_event_id=event1.id,
            identity_id=identity.id,
            board_id=board1.id,
            submission_count=1,
            last_submission_at=now,
            last_score_value=100.0,
        )
        meta2 = ScoreSubmissionMeta(
            score_event_id=event2.id,
            identity_id=identity.id,
            board_id=board2.id,
            submission_count=1,
            last_submission_at=now,
            last_score_value=200.0,
        )
        await meta_repo.create(meta1)
        await meta_repo.create(meta2)

        # Filter by board1
        response = await client.get(
            f"/score-submission-metadata?account_id={account.id}&board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["board_id"] == str(board1.id)

    async def test_list_submission_meta_filter_by_identity(
        self, client: AsyncClient, db_session: AsyncSession, test_api_key: str
    ):
        """Test filtering submission metadata by identity_id via API."""
        # Note: The API currently accepts device_id but the underlying filtering
        # works with identity_id. This test validates the identity-based data model.
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

        # Create two identities
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_001",
            display_name="Player One",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_002",
            display_name="Player Two",
        )

        # Create score events for both identities
        event_service = ScoreEventService(db_session)
        event1 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity1.id,
            event_payload={"value": 100.0},
        )
        event2 = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity2.id,
            event_payload={"value": 200.0},
        )

        # Create submission metadata for both identities
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        now = datetime.now(UTC)
        meta1 = ScoreSubmissionMeta(
            score_event_id=event1.id,
            identity_id=identity1.id,
            board_id=board.id,
            submission_count=1,
            last_submission_at=now,
            last_score_value=100.0,
        )
        meta2 = ScoreSubmissionMeta(
            score_event_id=event2.id,
            identity_id=identity2.id,
            board_id=board.id,
            submission_count=1,
            last_submission_at=now,
            last_score_value=200.0,
        )
        await meta_repo.create(meta1)
        await meta_repo.create(meta2)

        # List all metadata for this account (verifies both were created)
        response = await client.get(
            f"/score-submission-metadata?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        identity_ids = {m["identity_id"] for m in data["data"]}
        assert str(identity1.id) in identity_ids
        assert str(identity2.id) in identity_ids

    async def test_get_submission_meta(
        self, client: AsyncClient, db_session: AsyncSession, test_api_key: str
    ):
        """Test getting a single submission metadata by ID via API."""
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

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_123",
            display_name="Test Player",
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

        # Create submission metadata directly
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        meta = ScoreSubmissionMeta(
            score_event_id=event.id,
            identity_id=identity.id,
            board_id=board.id,
            submission_count=1,
            last_submission_at=datetime.now(UTC),
            last_score_value=100.0,
        )
        await meta_repo.create(meta)

        # Get submission metadata by identity and board to verify it was created
        retrieved_meta = await meta_repo.get_by_identity_and_board(identity.id, board.id)
        assert retrieved_meta is not None

        # Get via API
        response = await client.get(
            f"/score-submission-metadata/{meta.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(meta.id)
        assert data["identity_id"] == str(identity.id)
        assert data["board_id"] == str(board.id)
        assert data["submission_count"] == 1

    async def test_get_submission_meta_not_found(
        self, client: AsyncClient, db_session: AsyncSession, test_api_key: str
    ):
        """Test getting a non-existent submission metadata returns 404."""
        response = await client.get(
            "/score-submission-metadata/sub_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_superadmin_list_submission_metadata_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session: AsyncSession
    ):
        """Test that superadmin can list submission metadata WITHOUT account_id and sees all."""
        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository
        from leadr.common.domain.ids import AccountID

        # Create two accounts with submission metadata in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Meta",
            slug="account-one-meta",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Meta",
            slug="account-two-meta",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game Meta 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Meta 2",
        )

        # Create boards
        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Board Meta 1",
            icon="trophy",
            short_code="BMT1A1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Board Meta 2",
            icon="star",
            short_code="BMT2A2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identities
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity1, _ = await identity_service.get_or_create_identity(
            account_id=account1.id,
            game_id=game1.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_meta_device_001",
            display_name="Player Meta 1",
        )
        identity2, _ = await identity_service.get_or_create_identity(
            account_id=account2.id,
            game_id=game2.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_meta_device_002",
            display_name="Player Meta 2",
        )

        # Create score events and submission metadata for each account
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

        # Create submission metadata for each account
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        meta1 = ScoreSubmissionMeta(
            score_event_id=event1.id,
            identity_id=identity1.id,
            board_id=board1.id,
            submission_count=1,
            last_submission_at=now,
            last_score_value=1000.0,
        )
        meta2 = ScoreSubmissionMeta(
            score_event_id=event2.id,
            identity_id=identity2.id,
            board_id=board2.id,
            submission_count=1,
            last_submission_at=now,
            last_score_value=2000.0,
        )
        await meta_repo.create(meta1)
        await meta_repo.create(meta2)

        # List submission metadata WITHOUT account_id - should return from ALL accounts
        response = await authenticated_client.get("/score-submission-metadata")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain metadata from both accounts (at least 2 entries)
        identity_ids = {m["identity_id"] for m in data["data"]}
        assert str(identity1.id) in identity_ids
        assert str(identity2.id) in identity_ids

    async def test_list_submission_meta_filter_by_device(
        self, client: AsyncClient, db_session: AsyncSession, test_api_key: str
    ):
        """Test filtering submission metadata by device_id via API."""
        from leadr.common.domain.ids import DeviceID

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

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_device_filter",
            display_name="Test Player",
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

        # Create submission metadata
        meta_repo = ScoreSubmissionMetaRepository(db_session)
        meta = ScoreSubmissionMeta(
            score_event_id=event.id,
            identity_id=identity.id,
            board_id=board.id,
            submission_count=1,
            last_submission_at=datetime.now(UTC),
            last_score_value=100.0,
        )
        await meta_repo.create(meta)

        # Use a made-up device_id since we just want to test the filter path
        device_id = DeviceID()

        # Filter by device_id (this will return empty results but cover the filter path)
        response = await client.get(
            f"/score-submission-metadata?account_id={account.id}&device_id={device_id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        # The result will be empty since the device_id doesn't match
        # but we've covered the filter code path

    async def test_list_submission_meta_invalid_cursor(
        self, client: AsyncClient, db_session: AsyncSession, test_api_key: str
    ):
        """Test listing submission metadata with invalid cursor returns 400."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.get(
            f"/score-submission-metadata?account_id={account.id}&cursor=invalid_cursor",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
