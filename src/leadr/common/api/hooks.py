"""Request hooks for cloud/enterprise extensibility.

These hooks are no-ops in OSS but can be overridden via FastAPI dependency_overrides.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Protocol, TypeAlias, TypeVar

from fastapi import BackgroundTasks, Depends, Request

from leadr.auth.dependencies import AdminAuthContext, ClientAuthContext
from leadr.boards.api.board_schemas import BoardCreateRequest
from leadr.boards.api.board_template_schemas import (
    BoardTemplateCreateRequest,
    BoardTemplateUpdateRequest,
)
from leadr.common.domain.ids import AccountID
from leadr.games.api.game_schemas import GameCreateRequest
from leadr.scores.api.score_schemas import ScoreClientCreateRequest

# --- Generic hook protocols ---

RequestT = TypeVar("RequestT", contravariant=True)
AuthT = TypeVar("AuthT", contravariant=True)


class Hook(Protocol[RequestT, AuthT]):
    """Generic hook type for resource lifecycle events.

    All hooks follow the signature: (request, auth, background_tasks) -> None
    - request: The Pydantic request schema for the operation
    - auth: The authentication context (AdminAuthContext or ClientAuthContext)
    - background_tasks: FastAPI BackgroundTasks for scheduling async work
    """

    async def __call__(
        self, request: RequestT, auth: AuthT, background_tasks: BackgroundTasks
    ) -> None: ...


class UpdateHook(Protocol[RequestT, AuthT]):
    """Hook type for update operations that need the resource's account_id.

    Update hooks receive account_id separately since it comes from the existing
    resource, not the update request body.
    """

    async def __call__(
        self,
        account_id: AccountID,
        request: RequestT,
        auth: AuthT,
        background_tasks: BackgroundTasks,
    ) -> None: ...


# --- Hook type aliases ---
# Games - Admin auth
PreCreateGameHook: TypeAlias = Hook[GameCreateRequest, AdminAuthContext]
PostCreateGameHook: TypeAlias = Hook[GameCreateRequest, AdminAuthContext]

# Boards - Admin auth
PreCreateBoardHook: TypeAlias = Hook[BoardCreateRequest, AdminAuthContext]
PostCreateBoardHook: TypeAlias = Hook[BoardCreateRequest, AdminAuthContext]

# Scores - Client auth (score submissions are client-facing)
PreCreateScoreHook: TypeAlias = Hook[ScoreClientCreateRequest, ClientAuthContext]
PostCreateScoreHook: TypeAlias = Hook[ScoreClientCreateRequest, ClientAuthContext]

# Board templates - Admin auth
PreCreateBoardTemplateHook: TypeAlias = Hook[BoardTemplateCreateRequest, AdminAuthContext]
PreUpdateBoardTemplateHook: TypeAlias = UpdateHook[BoardTemplateUpdateRequest, AdminAuthContext]

# Rate limiting (uses raw Request, not schema)
RateLimitHook = Callable[[Request], Awaitable[None]]


# --- Registration hook protocol ---
# (Public endpoint, no auth context — data comes from created entities)


class PostCompleteRegistrationHook(Protocol):
    """Hook called after POST /register/complete succeeds.

    Fires for both new-account registration and invite-acceptance flows.
    Does not follow the standard Hook[RequestT, AuthT] pattern because
    /register/complete is a public endpoint with no auth context; the useful
    data comes from the created entities rather than the request body.
    """

    async def __call__(
        self,
        email: str,
        display_name: str,
        account_name: str,
        account_slug: str,
        background_tasks: BackgroundTasks,
    ) -> None: ...


# --- No-op implementations ---


async def noop_pre_create_game(
    request: GameCreateRequest, auth: AdminAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op pre-create game hook."""


async def noop_post_create_game(
    request: GameCreateRequest, auth: AdminAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op post-create game hook."""


async def noop_pre_create_board(
    request: BoardCreateRequest, auth: AdminAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op pre-create board hook."""


async def noop_post_create_board(
    request: BoardCreateRequest, auth: AdminAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op post-create board hook."""


async def noop_pre_create_score(
    request: ScoreClientCreateRequest, auth: ClientAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op pre-create score hook."""


async def noop_post_create_score(
    request: ScoreClientCreateRequest, auth: ClientAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op post-create score hook."""


async def noop_rate_limit_check(request: Request) -> None:
    """No-op rate limit hook."""


async def noop_pre_create_board_template(
    request: BoardTemplateCreateRequest, auth: AdminAuthContext, background_tasks: BackgroundTasks
) -> None:
    """No-op pre-create board template hook."""


async def noop_pre_update_board_template(
    account_id: AccountID,
    request: BoardTemplateUpdateRequest,
    auth: AdminAuthContext,
    background_tasks: BackgroundTasks,
) -> None:
    """No-op pre-update board template hook."""


async def noop_post_complete_registration(
    email: str,
    display_name: str,
    account_name: str,
    account_slug: str,
    background_tasks: BackgroundTasks,
) -> None:
    """No-op post-complete registration hook."""


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


def get_pre_create_board_template_hook() -> PreCreateBoardTemplateHook:
    """Get the pre-create board template hook. Override in cloud."""
    return noop_pre_create_board_template


def get_pre_update_board_template_hook() -> PreUpdateBoardTemplateHook:
    """Get the pre-update board template hook. Override in cloud."""
    return noop_pre_update_board_template


def get_post_complete_registration_hook() -> PostCompleteRegistrationHook:
    """Get the post-complete registration hook. Override in cloud."""
    return noop_post_complete_registration


# --- Injectable dependencies ---

PreCreateGameHookDep = Annotated[PreCreateGameHook, Depends(get_pre_create_game_hook)]
PostCreateGameHookDep = Annotated[PostCreateGameHook, Depends(get_post_create_game_hook)]
PreCreateBoardHookDep = Annotated[PreCreateBoardHook, Depends(get_pre_create_board_hook)]
PostCreateBoardHookDep = Annotated[PostCreateBoardHook, Depends(get_post_create_board_hook)]
PreCreateScoreHookDep = Annotated[PreCreateScoreHook, Depends(get_pre_create_score_hook)]
PostCreateScoreHookDep = Annotated[PostCreateScoreHook, Depends(get_post_create_score_hook)]
PreCreateBoardTemplateHookDep = Annotated[
    PreCreateBoardTemplateHook, Depends(get_pre_create_board_template_hook)
]
PreUpdateBoardTemplateHookDep = Annotated[
    PreUpdateBoardTemplateHook, Depends(get_pre_update_board_template_hook)
]
PostCompleteRegistrationHookDep = Annotated[
    PostCompleteRegistrationHook, Depends(get_post_complete_registration_hook)
]


# --- Router-level rate limit dependency ---


async def require_rate_limit_check(
    request: Request,
    hook: Annotated[RateLimitHook, Depends(get_rate_limit_hook)],
) -> None:
    """Rate limit dependency for router-level application."""
    await hook(request)
