"""Tests for test_mode functionality in Score API routes."""

import hashlib
from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.ids import DeviceID
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestClientScoreTestMode:
    """Test suite for test_mode in client score creation and listing."""

    async def test_create_score_in_test_mode_sets_is_test_true(
        self, client: AsyncClient, db_session
    ):
        """Test that scores created in test mode have is_test=True."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-testmode",
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
        )

        # Start client session WITH test_mode=true
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": device_fingerprint,
                "platform": "ios",
                "test_mode": True,
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]
        assert session_response.json()["test_mode"] is True

        # Get nonce for score creation
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce = nonce_response.json()["nonce_value"]

        # Create score via client API
        score_response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "player_name": "TestPlayer",
                "value": 1000.0,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce,
            },
        )
        assert score_response.status_code == 201
        score_data = score_response.json()
        assert score_data["is_test"] is True

    async def test_create_score_in_normal_mode_sets_is_test_false(
        self, client: AsyncClient, db_session
    ):
        """Test that scores created in normal mode have is_test=False."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account Normal",
            slug="test-account-normal",
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
        )

        # Start client session WITHOUT test_mode (defaults to false)
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": device_fingerprint,
                "platform": "android",
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]
        assert session_response.json()["test_mode"] is False

        # Get nonce for score creation
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert nonce_response.status_code == 200
        nonce = nonce_response.json()["nonce_value"]

        # Create score via client API
        score_response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "player_name": "NormalPlayer",
                "value": 2000.0,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": nonce,
            },
        )
        assert score_response.status_code == 201
        score_data = score_response.json()
        assert score_data["is_test"] is False

    async def test_client_list_scores_in_test_mode_returns_only_test_scores(
        self, client: AsyncClient, db_session
    ):
        """Test that client listing scores in test mode only sees test scores."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account List",
            slug="test-account-list",
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
        )

        # Create a production score
        score_service = ScoreService(db_session)
        prod_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="ProdPlayer",
            value=1000.0,
            is_test=False,
        )

        # Create a test score
        test_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="TestPlayer",
            value=2000.0,
            is_test=True,
        )

        # Start client session in test mode
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": device_fingerprint,
                "test_mode": True,
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # List scores - should only see test scores
        list_response = await client.get(
            f"/client/scores?board_id={board.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_response.status_code == 200
        scores = list_response.json()["data"]

        # Should only see the test score
        assert len(scores) == 1
        assert scores[0]["id"] == str(test_score.id)
        assert scores[0]["player_name"] == "TestPlayer"
        assert scores[0]["is_test"] is True

    async def test_client_list_scores_in_normal_mode_returns_only_prod_scores(
        self, client: AsyncClient, db_session
    ):
        """Test that client listing scores in normal mode only sees production scores."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account List Normal",
            slug="test-account-list-normal",
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
        )

        # Create a production score
        score_service = ScoreService(db_session)
        prod_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="ProdPlayer",
            value=1000.0,
            is_test=False,
        )

        # Create a test score
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="TestPlayer",
            value=2000.0,
            is_test=True,
        )

        # Start client session in normal mode (default)
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": device_fingerprint,
            },
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        # List scores - should only see production scores
        list_response = await client.get(
            f"/client/scores?board_id={board.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_response.status_code == 200
        scores = list_response.json()["data"]

        # Should only see the production score
        assert len(scores) == 1
        assert scores[0]["id"] == str(prod_score.id)
        assert scores[0]["player_name"] == "ProdPlayer"
        assert scores[0]["is_test"] is False


@pytest.mark.asyncio
class TestAdminScoreTestModeFilter:
    """Test suite for is_test filter in admin score listing."""

    async def test_admin_list_scores_default_excludes_test_scores(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that admin listing scores without is_test param excludes test scores."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account Admin",
            slug="test-account-admin",
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
        )

        # Create scores
        score_service = ScoreService(db_session)
        prod_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="ProdPlayer",
            value=1000.0,
            is_test=False,
        )

        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="TestPlayer",
            value=2000.0,
            is_test=True,
        )

        # List scores without is_test param (default should exclude test)
        list_response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}",
            headers={"leadr-api-key": test_api_key},
        )
        assert list_response.status_code == 200
        scores = list_response.json()["data"]

        # Should only see production scores
        assert len(scores) == 1
        assert scores[0]["id"] == str(prod_score.id)
        assert scores[0]["is_test"] is False

    async def test_admin_list_scores_is_test_true_returns_only_test_scores(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that admin listing scores with is_test=true returns only test scores."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account Admin True",
            slug="test-account-admin-true",
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
        )

        # Create scores
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="ProdPlayer",
            value=1000.0,
            is_test=False,
        )

        test_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="TestPlayer",
            value=2000.0,
            is_test=True,
        )

        # List scores with is_test=true
        list_response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&is_test=true",
            headers={"leadr-api-key": test_api_key},
        )
        assert list_response.status_code == 200
        scores = list_response.json()["data"]

        # Should only see test scores
        assert len(scores) == 1
        assert scores[0]["id"] == str(test_score.id)
        assert scores[0]["is_test"] is True

    async def test_admin_list_scores_is_test_false_excludes_test_scores(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that admin listing scores with is_test=false excludes test scores."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account Admin False",
            slug="test-account-admin-false",
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
        )

        # Create scores
        score_service = ScoreService(db_session)
        prod_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="ProdPlayer",
            value=1000.0,
            is_test=False,
        )

        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="TestPlayer",
            value=2000.0,
            is_test=True,
        )

        # List scores with is_test=false
        list_response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&is_test=false",
            headers={"leadr-api-key": test_api_key},
        )
        assert list_response.status_code == 200
        scores = list_response.json()["data"]

        # Should only see production scores
        assert len(scores) == 1
        assert scores[0]["id"] == str(prod_score.id)
        assert scores[0]["is_test"] is False

    async def test_admin_list_scores_is_test_all_returns_all_scores(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that admin listing scores with is_test=all returns both test and production."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account Admin All",
            slug="test-account-admin-all",
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
        )

        # Create scores
        score_service = ScoreService(db_session)
        prod_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="ProdPlayer",
            value=1000.0,
            is_test=False,
        )

        test_score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=DeviceID(uuid4()),
            player_name="TestPlayer",
            value=2000.0,
            is_test=True,
        )

        # List scores with is_test=all
        list_response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&is_test=all",
            headers={"leadr-api-key": test_api_key},
        )
        assert list_response.status_code == 200
        scores = list_response.json()["data"]

        # Should see both production and test scores
        assert len(scores) == 2
        score_ids = {s["id"] for s in scores}
        assert str(prod_score.id) in score_ids
        assert str(test_score.id) in score_ids

        # Verify both types are present
        is_test_values = {s["is_test"] for s in scores}
        assert is_test_values == {True, False}


@pytest.mark.asyncio
class TestScoreTestModeRanking:
    """Test that rankings are separate for test vs production scores."""

    async def test_test_scores_have_separate_rankings(self, client: AsyncClient, db_session):
        """Test that test scores rank within their own pool, not mixed with production."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account Ranking",
            slug="test-account-ranking",
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
        )

        # Create production scores with values 100, 200, 300
        score_service = ScoreService(db_session)
        for value in [100, 200, 300]:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=DeviceID(uuid4()),
                player_name=f"ProdPlayer{value}",
                value=float(value),
                is_test=False,
            )

        # Create test scores with values 150, 250
        for value in [150, 250]:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=DeviceID(uuid4()),
                player_name=f"TestPlayer{value}",
                value=float(value),
                is_test=True,
            )

        # Start test mode session
        device_fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "game_id": str(game.id),
                "client_fingerprint": device_fingerprint,
                "test_mode": True,
            },
        )
        access_token = session_response.json()["access_token"]

        # List test scores
        list_response = await client.get(
            f"/client/scores?board_id={board.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_response.status_code == 200
        scores = list_response.json()["data"]

        # Should only see 2 test scores
        assert len(scores) == 2

        # Check ranks - should be 1 and 2 (not mixed with prod scores)
        # With desc sort, 250 should be rank 1, 150 should be rank 2
        ranks = sorted([s["rank"] for s in scores])
        assert ranks == [1, 2]

        # Find the score with value 250 - it should be rank 1
        score_250 = next(s for s in scores if s["value"] == 250.0)
        assert score_250["rank"] == 1

        # Find the score with value 150 - it should be rank 2
        score_150 = next(s for s in scores if s["value"] == 150.0)
        assert score_150["rank"] == 2
