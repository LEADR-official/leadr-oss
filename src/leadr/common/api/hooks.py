"""Request hooks for cloud/enterprise extensibility.

These hooks are no-ops in OSS but can be overridden via FastAPI dependency_overrides.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import BackgroundTasks, Depends, Request

from leadr.auth.dependencies import AdminAuthContext, ClientAuthContext
from leadr.common.domain.ids import AccountID, GameID

# Type aliases for hook signatures
# Games/Boards: Admin-only routes
PreCreateGameHook = Callable[[AccountID, AdminAuthContext], Awaitable[None]]
PostCreateGameHook = Callable[[AccountID, AdminAuthContext, BackgroundTasks], Awaitable[None]]
PreCreateBoardHook = Callable[[AccountID, GameID, AdminAuthContext], Awaitable[None]]
PostCreateBoardHook = Callable[
    [AccountID, GameID, AdminAuthContext, BackgroundTasks], Awaitable[None]
]
# Scores: Client-only route (admin score creation doesn't consume quotas)
PreCreateScoreHook = Callable[[AccountID, ClientAuthContext], Awaitable[None]]
PostCreateScoreHook = Callable[[AccountID, ClientAuthContext, BackgroundTasks], Awaitable[None]]
RateLimitHook = Callable[[Request], Awaitable[None]]


# --- No-op implementations ---


async def noop_pre_create_game(account_id: AccountID, auth: AdminAuthContext) -> None:
    """No-op pre-create game hook."""


async def noop_post_create_game(
    account_id: AccountID, auth: AdminAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op post-create game hook."""


async def noop_pre_create_board(
    account_id: AccountID, game_id: GameID, auth: AdminAuthContext
) -> None:
    """No-op pre-create board hook."""


async def noop_post_create_board(
    account_id: AccountID,
    game_id: GameID,
    auth: AdminAuthContext,
    background_tasks: BackgroundTasks,
) -> None:
    """No-op post-create board hook."""


async def noop_pre_create_score(account_id: AccountID, auth: ClientAuthContext) -> None:
    """No-op pre-create score hook."""


async def noop_post_create_score(
    account_id: AccountID, auth: ClientAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op post-create score hook."""


async def noop_rate_limit_check(request: Request) -> None:
    """No-op rate limit hook."""


# --- Dependency factories (for override targets) ---


def get_pre_create_game_hook() -> PreCreateGameHook:
    """Get the pre-create game hook. Override in cloud."""
    return noop_pre_create_game


def get_post_create_game_hook() -> PostCreateGameHook:
    """Get the post-create game hook. Override in cloud."""
    return noop_post_create_game


def get_pre_create_board_hook() -> PreCreateBoardHook:
    """Get the pre-create board hook. Override in cloud."""
    return noop_pre_create_board


def get_post_create_board_hook() -> PostCreateBoardHook:
    """Get the post-create board hook. Override in cloud."""
    return noop_post_create_board


def get_pre_create_score_hook() -> PreCreateScoreHook:
    """Get the pre-create score hook. Override in cloud."""
    return noop_pre_create_score


def get_post_create_score_hook() -> PostCreateScoreHook:
    """Get the post-create score hook. Override in cloud."""
    return noop_post_create_score


def get_rate_limit_hook() -> RateLimitHook:
    """Get the rate limit hook. Override in cloud."""
    return noop_rate_limit_check


# --- Injectable dependencies ---

PreCreateGameHookDep = Annotated[PreCreateGameHook, Depends(get_pre_create_game_hook)]
PostCreateGameHookDep = Annotated[PostCreateGameHook, Depends(get_post_create_game_hook)]
PreCreateBoardHookDep = Annotated[PreCreateBoardHook, Depends(get_pre_create_board_hook)]
PostCreateBoardHookDep = Annotated[PostCreateBoardHook, Depends(get_post_create_board_hook)]
PreCreateScoreHookDep = Annotated[PreCreateScoreHook, Depends(get_pre_create_score_hook)]
PostCreateScoreHookDep = Annotated[PostCreateScoreHook, Depends(get_post_create_score_hook)]


# --- Router-level rate limit dependency ---


async def require_rate_limit_check(
    request: Request,
    hook: Annotated[RateLimitHook, Depends(get_rate_limit_hook)],
) -> None:
    """Rate limit dependency for router-level application."""
    await hook(request)
