"""Tests for request hooks module."""

from unittest.mock import MagicMock

import pytest
from fastapi import Request

from leadr.auth.dependencies import AdminAuthContext, ClientAuthContext
from leadr.common.api.hooks import (
    PostCreateBoardHookDep,
    PostCreateGameHookDep,
    PostCreateScoreHookDep,
    PreCreateBoardHookDep,
    PreCreateGameHookDep,
    PreCreateScoreHookDep,
    get_post_create_board_hook,
    get_post_create_game_hook,
    get_post_create_score_hook,
    get_pre_create_board_hook,
    get_pre_create_game_hook,
    get_pre_create_score_hook,
    get_rate_limit_hook,
    noop_post_create_board,
    noop_post_create_game,
    noop_post_create_score,
    noop_pre_create_board,
    noop_pre_create_game,
    noop_pre_create_score,
    noop_rate_limit_check,
    require_rate_limit_check,
)
from leadr.common.domain.ids import AccountID, GameID


class TestNoopHooks:
    """Test that all no-op hooks execute without error."""

    @pytest.mark.asyncio
    async def test_noop_pre_create_game(self) -> None:
        """Test noop_pre_create_game executes without error."""
        account_id = AccountID()
        auth = MagicMock(spec=AdminAuthContext)

        # Should not raise
        await noop_pre_create_game(account_id, auth)

    @pytest.mark.asyncio
    async def test_noop_post_create_game(self) -> None:
        """Test noop_post_create_game executes without error."""
        account_id = AccountID()
        auth = MagicMock(spec=AdminAuthContext)

        # Should not raise
        await noop_post_create_game(account_id, auth)

    @pytest.mark.asyncio
    async def test_noop_pre_create_board(self) -> None:
        """Test noop_pre_create_board executes without error."""
        account_id = AccountID()
        game_id = GameID()
        auth = MagicMock(spec=AdminAuthContext)

        # Should not raise
        await noop_pre_create_board(account_id, game_id, auth)

    @pytest.mark.asyncio
    async def test_noop_post_create_board(self) -> None:
        """Test noop_post_create_board executes without error."""
        account_id = AccountID()
        game_id = GameID()
        auth = MagicMock(spec=AdminAuthContext)

        # Should not raise
        await noop_post_create_board(account_id, game_id, auth)

    @pytest.mark.asyncio
    async def test_noop_pre_create_score(self) -> None:
        """Test noop_pre_create_score executes without error."""
        account_id = AccountID()
        auth = MagicMock(spec=ClientAuthContext)

        # Should not raise
        await noop_pre_create_score(account_id, auth)

    @pytest.mark.asyncio
    async def test_noop_post_create_score(self) -> None:
        """Test noop_post_create_score executes without error."""
        account_id = AccountID()
        auth = MagicMock(spec=ClientAuthContext)

        # Should not raise
        await noop_post_create_score(account_id, auth)

    @pytest.mark.asyncio
    async def test_noop_rate_limit_check(self) -> None:
        """Test noop_rate_limit_check executes without error."""
        request = MagicMock(spec=Request)

        # Should not raise
        await noop_rate_limit_check(request)


class TestHookFactories:
    """Test that hook factories return the correct no-op implementations."""

    def test_get_pre_create_game_hook(self) -> None:
        """Test get_pre_create_game_hook returns noop implementation."""
        hook = get_pre_create_game_hook()
        assert hook is noop_pre_create_game

    def test_get_post_create_game_hook(self) -> None:
        """Test get_post_create_game_hook returns noop implementation."""
        hook = get_post_create_game_hook()
        assert hook is noop_post_create_game

    def test_get_pre_create_board_hook(self) -> None:
        """Test get_pre_create_board_hook returns noop implementation."""
        hook = get_pre_create_board_hook()
        assert hook is noop_pre_create_board

    def test_get_post_create_board_hook(self) -> None:
        """Test get_post_create_board_hook returns noop implementation."""
        hook = get_post_create_board_hook()
        assert hook is noop_post_create_board

    def test_get_pre_create_score_hook(self) -> None:
        """Test get_pre_create_score_hook returns noop implementation."""
        hook = get_pre_create_score_hook()
        assert hook is noop_pre_create_score

    def test_get_post_create_score_hook(self) -> None:
        """Test get_post_create_score_hook returns noop implementation."""
        hook = get_post_create_score_hook()
        assert hook is noop_post_create_score

    def test_get_rate_limit_hook(self) -> None:
        """Test get_rate_limit_hook returns noop implementation."""
        hook = get_rate_limit_hook()
        assert hook is noop_rate_limit_check


class TestRequireRateLimitCheck:
    """Test the router-level rate limit dependency."""

    @pytest.mark.asyncio
    async def test_require_rate_limit_check_calls_hook(self) -> None:
        """Test require_rate_limit_check invokes the provided hook."""
        request = MagicMock(spec=Request)
        called = []

        async def custom_hook(req: Request) -> None:
            called.append(req)

        await require_rate_limit_check(request, custom_hook)

        assert len(called) == 1
        assert called[0] is request

    @pytest.mark.asyncio
    async def test_require_rate_limit_check_with_noop_hook(self) -> None:
        """Test require_rate_limit_check works with noop hook."""
        request = MagicMock(spec=Request)

        # Should not raise
        await require_rate_limit_check(request, noop_rate_limit_check)


class TestHookTypeAliases:
    """Test that hook type aliases are properly defined."""

    def test_pre_create_game_hook_dep_exists(self) -> None:
        """Test PreCreateGameHookDep type alias is importable."""
        # Just verify import worked - done at module level
        assert PreCreateGameHookDep is not None

    def test_post_create_game_hook_dep_exists(self) -> None:
        """Test PostCreateGameHookDep type alias is importable."""
        assert PostCreateGameHookDep is not None

    def test_pre_create_board_hook_dep_exists(self) -> None:
        """Test PreCreateBoardHookDep type alias is importable."""
        assert PreCreateBoardHookDep is not None

    def test_post_create_board_hook_dep_exists(self) -> None:
        """Test PostCreateBoardHookDep type alias is importable."""
        assert PostCreateBoardHookDep is not None

    def test_pre_create_score_hook_dep_exists(self) -> None:
        """Test PreCreateScoreHookDep type alias is importable."""
        assert PreCreateScoreHookDep is not None

    def test_post_create_score_hook_dep_exists(self) -> None:
        """Test PostCreateScoreHookDep type alias is importable."""
        assert PostCreateScoreHookDep is not None
