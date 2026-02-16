"""Tests for Score API routes (mocked service layer)."""

import pytest
from httpx import AsyncClient

from leadr.auth.dependencies import require_admin_auth
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, GameID, IdentityID
from leadr.common.domain.pagination import CursorPosition
from leadr.scores.domain.anti_cheat.enums import FlagAction
from tests.conftest import make_admin_auth
from tests.leadr.scores.api.conftest import (
    make_anti_cheat_result,
    make_board,
    make_board_state,
    make_paginated_result,
    make_run_entry,
    make_score_event,
)


@pytest.mark.asyncio
class TestScoreRoutesAdmin:
    """Test suite for Admin Score API routes."""

    async def test_get_score_by_id_board_state(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
    ):
        """Test getting a BoardState score by ID returns rank."""
        # Arrange
        board = make_board(
            account_id=admin_auth.account_id,
            game_id=GameID(),
            sort_direction=SortDirection.DESCENDING,
        )
        state = make_board_state(
            board_id=board.id,
            identity_id=IdentityID(),
            primary_value=500.0,
            player_name="Player1",
            rank=1,  # Highest score gets rank 1
        )

        # Mock service to return (state, board, rank)
        mock_score_service.get_score_by_id.return_value = (state, board, 1)

        # Act
        score_id = f"scr_{state.id.uuid}"
        response = await mock_client_no_db.get(f"/scores/{score_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == score_id
        assert data["rank"] == 1

    async def test_get_score_by_id_run_entry(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
    ):
        """Test getting a RunEntry score by ID."""
        # Arrange
        board = make_board(
            account_id=admin_auth.account_id,
            game_id=GameID(),
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )
        entry = make_run_entry(
            board_id=board.id,
            identity_id=IdentityID(),
            primary_value=120.5,
            player_name="Runner",
            rank=1,
        )

        # Mock service
        mock_score_service.get_score_by_id.return_value = (entry, board, 1)

        # Act
        score_id = f"scr_{entry.id.uuid}"
        response = await mock_client_no_db.get(f"/scores/{score_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == score_id
        assert data["value"] == 120.5

    async def test_get_score_not_found(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
    ):
        """Test getting a non-existent score returns 404."""
        # Arrange
        mock_score_service.get_score_by_id.side_effect = EntityNotFoundError(
            "Score", "scr_00000000-0000-0000-0000-000000000000"
        )

        # Act
        response = await mock_client_no_db.get("/scores/scr_00000000-0000-0000-0000-000000000000")

        # Assert
        assert response.status_code == 404

    async def test_get_score_forbidden_different_account(
        self,
        mock_client_no_db: AsyncClient,
        mock_score_service,
        test_app,
    ):
        """Test that accessing a score from another account is forbidden for non-superadmins."""
        # Arrange - create non-superadmin auth for Account 2
        account1_id = AccountID()
        account2_id = AccountID()

        # Override auth to be a non-superadmin from account2
        non_super_auth = make_admin_auth(account_id=account2_id, is_superadmin=False)
        test_app.dependency_overrides[require_admin_auth] = lambda: non_super_auth

        # Score belongs to account1
        board = make_board(account_id=account1_id)
        state = make_board_state(board_id=board.id, primary_value=500.0)

        # Mock service
        mock_score_service.get_score_by_id.return_value = (state, board, 1)

        # Act
        score_id = f"scr_{state.id.uuid}"
        response = await mock_client_no_db.get(f"/scores/{score_id}")

        # Assert
        assert response.status_code == 403
        assert "access" in response.json()["error"].lower()

    async def test_list_scores_requires_board_id(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that list scores requires board_id."""
        # Act
        response = await mock_client_no_db.get("/scores")

        # Assert
        assert response.status_code == 400
        assert "board_id is required" in response.json()["error"]

    async def test_list_scores_board_not_found(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test list scores with non-existent board."""
        # Arrange
        mock_board_service.get_by_id.return_value = None

        # Act
        response = await mock_client_no_db.get(
            "/scores?board_id=brd_00000000-0000-0000-0000-000000000000"
        )

        # Assert
        assert response.status_code == 404

    async def test_list_scores_with_pagination(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test listing scores with pagination."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        # Create 15 board states with ranks
        states = [
            make_board_state(
                board_id=board.id,
                identity_id=IdentityID(),
                primary_value=float(i * 100),
                player_name=f"Player{i}",
                rank=i + 1,
            )
            for i in range(15)
        ]

        # Mock service to return first 5 items with has_next=True
        result = make_paginated_result(
            items=states[:5],
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=(float(400),), entity_id=str(states[4].id.uuid)),
        )
        mock_score_service.list_scores.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/scores?board_id={board.id}&limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["has_next"] is True

    async def test_list_scores_around_score_id(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test listing scores centered around a specific score."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        # Create states around the target (middle score)
        states = [
            make_board_state(
                board_id=board.id,
                primary_value=float((i + 1) * 100),
                rank=10 - i,  # Descending ranks
            )
            for i in range(10)
        ]
        target_state = states[4]  # 500 points, rank 6

        # Mock service to return window around target
        result = make_paginated_result(items=states[2:7], has_next=False, has_prev=False)
        mock_score_service.list_scores.return_value = result

        # Act
        score_id = f"scr_{target_state.id.uuid}"
        response = await mock_client_no_db.get(
            f"/scores?board_id={board.id}&around_score_id={score_id}&limit=5"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5

    async def test_list_scores_around_score_id_and_cursor_mutually_exclusive(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that around_score_id and cursor cannot be used together."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        # Act - try to use both cursor and around_score_id
        response = await mock_client_no_db.get(
            f"/scores?board_id={board.id}&around_score_id=scr_00000000-0000-0000-0000-000000000000&cursor=some_cursor"
        )

        # Assert
        assert response.status_code == 400
        assert "cursor" in response.json()["error"].lower()

    async def test_list_scores_around_score_id_requires_board_id(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that around_score_id requires board_id."""
        # Act
        response = await mock_client_no_db.get(
            "/scores?around_score_id=scr_00000000-0000-0000-0000-000000000000"
        )

        # Assert
        assert response.status_code == 400

    async def test_list_scores_around_score_value(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test listing scores around a hypothetical value."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        # Create states: 100, 200, 300, 400, 500
        states = [
            make_board_state(
                board_id=board.id,
                primary_value=float((i + 1) * 100),
                rank=5 - i,
            )
            for i in range(5)
        ]

        # Add a placeholder for value 250
        placeholder = make_board_state(
            board_id=board.id,
            primary_value=250.0,
            is_placeholder=True,
            rank=4,
        )

        # Mock service to return states with placeholder inserted
        result = make_paginated_result(
            items=[states[4], states[3], placeholder, states[2], states[1]]
        )
        mock_score_service.list_scores.return_value = result

        # Act
        response = await mock_client_no_db.get(
            f"/scores?board_id={board.id}&around_score_value=250&limit=5"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        placeholders = [d for d in data["data"] if d.get("is_placeholder")]
        assert len(placeholders) == 1
        assert placeholders[0]["value"] == 250.0

    async def test_list_scores_around_score_value_requires_board_id(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that around_score_value requires board_id."""
        # Act
        response = await mock_client_no_db.get("/scores?around_score_value=100")

        # Assert
        assert response.status_code == 400

    async def test_list_scores_around_score_value_and_cursor_mutually_exclusive(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that around_score_value and cursor cannot be used together."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        # Act
        response = await mock_client_no_db.get(
            f"/scores?board_id={board.id}&around_score_value=250&cursor=some_cursor"
        )

        # Assert
        assert response.status_code == 400
        assert "cursor" in response.json()["error"].lower()

    async def test_list_scores_admin_invalid_cursor(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_board_service,
        mock_score_service,
    ):
        """Test list scores with invalid cursor returns 400."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        # Mock service to raise validation error
        mock_score_service.list_scores.side_effect = CursorValidationError("Invalid cursor")

        # Act
        response = await mock_client_no_db.get(
            f"/scores?board_id={board.id}&cursor=invalid_cursor_value"
        )

        # Assert
        assert response.status_code == 400

    async def test_list_scores_admin_with_identity_filter(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test listing admin scores filtered by identity_id."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        identity1_id = IdentityID()

        # Create two states
        state1 = make_board_state(
            board_id=board.id,
            identity_id=identity1_id,
            primary_value=500.0,
            player_name="PlayerA",
            rank=1,
        )

        # Mock service to return only identity1's state (filtered)
        result = make_paginated_result(items=[state1])
        mock_score_service.list_scores.return_value = result

        # Act
        response = await mock_client_no_db.get(
            f"/scores?board_id={board.id}&identity_id={identity1_id}&is_test=all"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "PlayerA"

    async def test_list_scores_admin_with_pagination_cursors(
        self,
        mock_client_no_db: AsyncClient,
        admin_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that admin list_scores returns proper pagination cursors."""
        # Arrange
        board = make_board(account_id=admin_auth.account_id)
        mock_board_service.get_by_id.return_value = board

        states = [
            make_board_state(board_id=board.id, primary_value=float(i * 100), rank=i + 1)
            for i in range(10)
        ]

        # First page
        result1 = make_paginated_result(
            items=states[:3],
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=(float(200),), entity_id=str(states[2].id.uuid)),
        )
        mock_score_service.list_scores.return_value = result1

        # Act - first page
        response = await mock_client_no_db.get(f"/scores?board_id={board.id}&limit=3&is_test=all")

        # Assert - first page
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["next_cursor"] is not None

        # Arrange - second page
        result2 = make_paginated_result(
            items=states[3:6],
            has_next=True,
            has_prev=True,
            prev_position=CursorPosition(values=(float(200),), entity_id=str(states[2].id.uuid)),
            next_position=CursorPosition(values=(float(500),), entity_id=str(states[5].id.uuid)),
        )
        mock_score_service.list_scores.return_value = result2

        # Act - second page
        next_cursor = data["pagination"]["next_cursor"]
        response2 = await mock_client_no_db.get(
            f"/scores?board_id={board.id}&limit=3&cursor={next_cursor}&is_test=all"
        )

        # Assert - second page
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["data"]) == 3
        assert data2["pagination"]["prev_cursor"] is not None


@pytest.mark.asyncio
class TestScoreRoutesClient:
    """Test suite for Client Score API routes."""

    async def test_create_score_run_identity_board(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
        mock_identity_service,
        mock_hooks,
    ):
        """Test creating a score on a RUN_IDENTITY board."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )
        mock_board_service.get_by_id.return_value = board

        identity = client_auth.identity
        mock_identity_service.update_identity.return_value = identity

        event = make_score_event(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
        )
        state = make_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=1000.0,
            player_name="TestPlayer",
        )
        anti_cheat_result = make_anti_cheat_result(action=FlagAction.ACCEPT)

        mock_score_service.submit_score.return_value = (event, state, anti_cheat_result)

        # Act
        response = await mock_client_no_db.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 1000.0,
                "player_name": "TestPlayer",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["value"] == 1000.0
        assert data["player_name"] == "TestPlayer"

        # Verify hooks were called
        pre_hook, post_hook = mock_hooks
        assert pre_hook.called
        assert post_hook.called

    async def test_create_score_board_not_found(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
        mock_identity_service,
        mock_hooks,
    ):
        """Test creating a score on non-existent board returns 404."""
        # Arrange
        mock_board_service.get_by_id.return_value = None
        mock_identity_service.update_identity.return_value = client_auth.identity

        # Act
        response = await mock_client_no_db.post(
            "/client/scores",
            json={
                "board_id": "brd_00000000-0000-0000-0000-000000000000",
                "value": 100.0,
                "player_name": "TestPlayer",
            },
        )

        # Assert
        assert response.status_code == 404

    async def test_create_score_board_wrong_game(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
        mock_identity_service,
        mock_hooks,
    ):
        """Test creating a score on a board from a different game."""
        # Arrange
        wrong_game_id = GameID()  # Different from client_auth.game_id
        board = make_board(account_id=client_auth.account_id, game_id=wrong_game_id)
        mock_board_service.get_by_id.return_value = board
        mock_identity_service.update_identity.return_value = client_auth.identity

        # Act
        response = await mock_client_no_db.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 100.0,
                "player_name": "TestPlayer",
            },
        )

        # Assert
        assert response.status_code == 400
        assert "does not belong" in response.json()["error"].lower()

    async def test_create_score_anti_cheat_reject(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
        mock_identity_service,
        mock_hooks,
    ):
        """Test that anti-cheat REJECT returns 429."""
        # Arrange
        board = make_board(account_id=client_auth.account_id, game_id=client_auth.game_id)
        mock_board_service.get_by_id.return_value = board
        mock_identity_service.update_identity.return_value = client_auth.identity

        event = make_score_event(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            board_id=board.id,
            identity_id=client_auth.identity.id,
            value=1000.0,
        )
        reject_result = make_anti_cheat_result(
            action=FlagAction.REJECT, reason="Rate limit exceeded"
        )

        mock_score_service.submit_score.return_value = (event, None, reject_result)

        # Act
        response = await mock_client_no_db.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "value": 1000.0,
                "player_name": "TestPlayer",
            },
        )

        # Assert
        assert response.status_code == 429
        assert "Rate limit" in response.json()["error"]

    async def test_get_score_client(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
    ):
        """Test getting a score via client API."""
        # Arrange
        board = make_board(account_id=client_auth.account_id, game_id=client_auth.game_id)
        state = make_board_state(
            board_id=board.id, primary_value=500.0, player_name="TestPlayer", rank=1
        )

        mock_score_service.get_score_by_id.return_value = (state, board, 1)

        # Act
        score_id = f"scr_{state.id.uuid}"
        response = await mock_client_no_db.get(f"/client/scores/{score_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 500.0

    async def test_get_score_client_wrong_game(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
    ):
        """Test getting a score from a different game returns 403."""
        # Arrange
        wrong_game_id = GameID()
        board = make_board(account_id=client_auth.account_id, game_id=wrong_game_id)
        state = make_board_state(board_id=board.id, primary_value=500.0)

        mock_score_service.get_score_by_id.return_value = (state, board, 1)

        # Act
        score_id = f"scr_{state.id.uuid}"
        response = await mock_client_no_db.get(f"/client/scores/{score_id}")

        # Assert
        assert response.status_code == 403

    async def test_list_scores_client(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test listing scores via client API."""
        # Arrange
        board = make_board(account_id=client_auth.account_id, game_id=client_auth.game_id)
        mock_board_service.get_by_id.return_value = board

        state = make_board_state(
            board_id=board.id, primary_value=500.0, player_name="TestPlayer", rank=1
        )
        result = make_paginated_result(items=[state])
        mock_score_service.list_scores.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/client/scores?board_id={board.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    async def test_list_scores_client_with_identity_filter(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test listing client scores filtered by identity_id."""
        # Arrange
        board = make_board(account_id=client_auth.account_id, game_id=client_auth.game_id)
        mock_board_service.get_by_id.return_value = board

        identity_id = client_auth.identity.id
        state = make_board_state(
            board_id=board.id,
            identity_id=identity_id,
            primary_value=500.0,
            player_name="TestPlayer",
            rank=1,
        )

        result = make_paginated_result(items=[state])
        mock_score_service.list_scores.return_value = result

        # Act
        response = await mock_client_no_db.get(
            f"/client/scores?board_id={board.id}&identity_id={identity_id}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "TestPlayer"

    async def test_list_scores_client_identity_id_me_resolves_to_current_identity(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that identity_id=me resolves to the authenticated identity."""
        # Arrange
        board = make_board(account_id=client_auth.account_id, game_id=client_auth.game_id)
        mock_board_service.get_by_id.return_value = board

        identity_id = client_auth.identity.id
        state = make_board_state(
            board_id=board.id,
            identity_id=identity_id,
            primary_value=500.0,
            player_name="TestPlayer",
            rank=1,
        )

        result = make_paginated_result(items=[state])
        mock_score_service.list_scores.return_value = result

        # Act - pass "me" as identity_id
        response = await mock_client_no_db.get(f"/client/scores?board_id={board.id}&identity_id=me")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "TestPlayer"

        # Verify "me" was resolved to the actual identity_id
        call_kwargs = mock_score_service.list_scores.call_args.kwargs
        assert call_kwargs["identity_id"] == identity_id

    async def test_list_scores_client_run_runs_board(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test listing client scores from a RUN_RUNS board returns RunEntry data."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
            sort_direction=SortDirection.ASCENDING,
        )
        mock_board_service.get_by_id.return_value = board

        entries = [
            make_run_entry(
                board_id=board.id,
                primary_value=float(100 + i * 10),
                player_name="Speedrunner",
                rank=i + 1,
            )
            for i in range(3)
        ]
        result = make_paginated_result(items=entries)
        mock_score_service.list_scores.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/client/scores?board_id={board.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3

    async def test_get_score_client_run_entry(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
    ):
        """Test getting a RunEntry score via client API."""
        # Arrange
        board = make_board(
            account_id=client_auth.account_id,
            game_id=client_auth.game_id,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )
        entry = make_run_entry(
            board_id=board.id, primary_value=120.5, player_name="Speedrunner", rank=1
        )

        mock_score_service.get_score_by_id.return_value = (entry, board, 1)

        # Act
        score_id = f"scr_{entry.id.uuid}"
        response = await mock_client_no_db.get(f"/client/scores/{score_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 120.5

    async def test_list_scores_client_with_pagination(
        self,
        mock_client_no_db: AsyncClient,
        client_auth,
        mock_score_service,
        mock_board_service,
    ):
        """Test that client list_scores returns proper pagination metadata."""
        # Arrange
        board = make_board(account_id=client_auth.account_id, game_id=client_auth.game_id)
        mock_board_service.get_by_id.return_value = board

        states = [
            make_board_state(board_id=board.id, primary_value=float(i * 100), rank=i + 1)
            for i in range(10)
        ]

        result = make_paginated_result(
            items=states[:3],
            has_next=True,
            has_prev=False,
            next_position=CursorPosition(values=(float(200),), entity_id=str(states[2].id.uuid)),
        )
        mock_score_service.list_scores.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/client/scores?board_id={board.id}&limit=3")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["next_cursor"] is not None
