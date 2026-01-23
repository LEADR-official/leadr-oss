"""Main FastAPI application."""

import importlib.metadata
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.types import Lifespan

from api.middleware import AccessLogMiddleware, GeoIPMiddleware
from api.routes import router as api_router
from leadr.accounts.api.account_routes import router as account_router
from leadr.accounts.api.user_routes import router as user_router
from leadr.auth.api.api_key_routes import router as api_key_router
from leadr.auth.api.client_routes import (
    protected_router as client_protected_router,
)
from leadr.auth.api.client_routes import (
    public_router as client_public_router,
)
from leadr.auth.api.device_routes import router as device_router
from leadr.auth.api.device_session_routes import router as device_session_router
from leadr.auth.api.identity_routes import router as identity_router
from leadr.auth.api.identity_session_routes import router as identity_session_router
from leadr.auth.bootstrap import ensure_superadmin_exists
from leadr.auth.dependencies import require_admin_auth
from leadr.auth.services.nonce_tasks import cleanup_expired_nonces
from leadr.boards.api.board_routes import client_router as board_client_router
from leadr.boards.api.board_routes import router as board_router
from leadr.boards.api.board_state_routes import router as board_state_router
from leadr.boards.api.board_template_routes import router as board_template_router
from leadr.boards.api.run_entry_routes import router as run_entry_router
from leadr.boards.services.board_tasks import expire_boards, process_due_templates
from leadr.common.api.exceptions import (
    catchall_exception_handler,
    entity_not_found_handler,
    http_exception_handler,
    validation_error_handler,
)
from leadr.common.api.hooks import require_rate_limit_check
from leadr.common.background_tasks import get_scheduler
from leadr.common.database import async_session_factory, engine
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.geoip import GeoIPService
from leadr.config import settings
from leadr.games.api.game_routes import router as game_router
from leadr.logging import setup_logging
from leadr.registration.api.routes import public_router as registration_public_router
from leadr.registration.api.routes import router as jam_code_router
from leadr.scores.api.score_event_routes import router as score_event_router
from leadr.scores.api.score_flag_routes import router as score_flag_router
from leadr.scores.api.score_routes import client_router as score_client_router
from leadr.scores.api.score_routes import router as score_router
from leadr.scores.api.score_submission_meta_routes import router as score_submission_meta_router

# Initialize structured logging before any loggers are used
setup_logging(
    log_level="DEBUG" if settings.DEBUG else "INFO",
    json_format=settings.LOG_JSON,
    log_to_file=settings.LOG_TO_FILE,
    log_dir=settings.LOG_DIR,
    app_name=settings.APP,
    env=settings.ENV,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage OSS application lifespan events.

    This can be imported and wrapped by extending applications (e.g., LEADR Cloud)
    to add their own startup/shutdown logic while preserving OSS behavior.
    """
    # Startup: Database engine is already created at module import
    # The engine will establish connections as needed from the pool

    # Initialize GeoIP service (skip in test environment to avoid network calls)
    if settings.ENV != "TEST":
        geoip_service = GeoIPService(
            account_id=settings.MAXMIND_ACCOUNT_ID,
            license_key=settings.MAXMIND_LICENSE_KEY,
            city_db_url=settings.MAXMIND_CITY_DB_URL,
            country_db_url=settings.MAXMIND_COUNTRY_DB_URL,
            database_path=settings.GEOIP_DATABASE_PATH,
            refresh_days=settings.GEOIP_REFRESH_DAYS,
            download_enabled=settings.GEOIP_DOWNLOAD_ENABLED,
        )
        await geoip_service.initialize()
        app.state.geoip_service = geoip_service
    else:
        # In tests, GeoIP service is None - middleware handles gracefully
        # Tests can override with mocks if needed via app.dependency_overrides
        app.state.geoip_service = None

    # Bootstrap superadmin user if none exists
    async with async_session_factory() as session:
        await ensure_superadmin_exists(session)

    # Register and start background tasks
    scheduler = get_scheduler()

    # Ensure we only run background tasks one API instance
    if settings.ENABLE_ADMIN_API:
        scheduler.add_task(
            "process-due-templates",
            process_due_templates,
            interval_seconds=settings.BACKGROUND_TASK_TEMPLATE_INTERVAL,
        )
        scheduler.add_task(
            "expire-boards",
            expire_boards,
            interval_seconds=settings.BACKGROUND_TASK_EXPIRE_INTERVAL,
        )
        scheduler.add_task(
            "cleanup-expired-nonces",
            cleanup_expired_nonces,
            interval_seconds=settings.BACKGROUND_TASK_NONCE_CLEANUP_INTERVAL,
        )
    await scheduler.start()

    yield

    # Shutdown: Stop background tasks, close GeoIP service, and dispose of database engine
    await scheduler.stop()
    if hasattr(app.state, "geoip_service") and app.state.geoip_service is not None:
        app.state.geoip_service.close()
    await engine.dispose()


DEFAULT_DESCRIPTION = (
    "LEADR Open-Source Edition is the free cross-platform leaderboard backend for game devs"
)


def _get_api_title() -> str:
    """Get default API title based on enabled APIs."""
    if settings.ENABLE_ADMIN_API and settings.ENABLE_CLIENT_API:
        return "LEADR Open-Source Edition - Admin & Client API"
    elif settings.ENABLE_ADMIN_API:
        return "LEADR Open-Source Edition - Admin API"
    elif settings.ENABLE_CLIENT_API:
        return "LEADR Open-Source Edition - Client API"
    else:
        raise RuntimeError("One or both of ENABLE_ADMIN_API or ENABLE_CLIENT_API must be TRUE")


def create_app(
    *,
    title: str | None = None,
    description: str | None = None,
    version: str | None = None,
    lifespan_override: Lifespan[FastAPI] | None = None,
) -> FastAPI:
    """Create and configure a LEADR FastAPI application.

    This factory function allows extending applications (e.g., LEADR Cloud) to customize
    the app's metadata and lifespan while reusing all OSS routes, middleware, and handlers.

    Args:
        title: Override the default API title. Defaults to a title based on enabled APIs.
        description: Override the default API description.
        version: Override the default version. Defaults to leadr-oss package version.
        lifespan_override: Custom lifespan context manager. If provided, it should call
                  lifespan() internally to ensure OSS startup/shutdown runs.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=title or _get_api_title(),
        description=description or DEFAULT_DESCRIPTION,
        version=version or importlib.metadata.version("leadr-oss"),
        lifespan=lifespan_override or lifespan,
    )

    # Register exception handlers
    app.add_exception_handler(EntityNotFoundError, entity_not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, catchall_exception_handler)  # type: ignore[arg-type]

    # Add middleware (order matters - last added runs first)
    # GeoIP middleware runs first to attach geo data
    app.add_middleware(GeoIPMiddleware, dev_override_ip=settings.DEV_OVERRIDE_IP)
    # Access log middleware runs last (outermost) to capture full request timing
    app.add_middleware(AccessLogMiddleware)

    # Create public and admin routers with separate authentication requirements
    public_router = APIRouter()
    client_router = APIRouter(
        prefix=f"{settings.API_PREFIX}/client",
        dependencies=[Depends(require_rate_limit_check)],
    )
    admin_router = APIRouter(
        dependencies=[Depends(require_admin_auth), Depends(require_rate_limit_check)]
    )

    # Public routes - accessible without authentication
    public_router.include_router(api_router)
    public_router.include_router(registration_public_router, tags=["Registration"])

    # Client routes - require client auth flow
    client_router.include_router(client_protected_router, tags=["Authentication"])
    client_router.include_router(board_client_router, tags=["Scores"])
    client_router.include_router(score_client_router, tags=["Scores"])

    # Admin routes - require API key authentication
    admin_router.include_router(account_router, tags=["Accounts"])
    admin_router.include_router(user_router, tags=["Users"])
    admin_router.include_router(api_key_router, tags=["API Keys"])
    admin_router.include_router(game_router, tags=["Games"])
    admin_router.include_router(board_router, tags=["Boards"])
    admin_router.include_router(board_state_router, tags=["Board States"])
    admin_router.include_router(board_template_router, tags=["Board Templates"])
    admin_router.include_router(run_entry_router, tags=["Run Entries"])
    admin_router.include_router(score_router, tags=["Scores"])
    admin_router.include_router(score_event_router, tags=["Score Events"])
    admin_router.include_router(score_flag_router, tags=["Score Flags"])
    admin_router.include_router(score_submission_meta_router, tags=["Score Submission Metadata"])
    admin_router.include_router(device_router, tags=["Devices"])
    admin_router.include_router(device_session_router, tags=["Device Sessions"])
    admin_router.include_router(identity_router, tags=["Identities"])
    admin_router.include_router(identity_session_router, tags=["Identity Sessions"])
    admin_router.include_router(jam_code_router, tags=["Registration"])

    # Include admin router only when Admin API is enabled
    if settings.ENABLE_ADMIN_API:
        app.include_router(admin_router, prefix=settings.API_PREFIX)

    # Include client router only when Client API is enabled
    if settings.ENABLE_CLIENT_API:
        app.include_router(client_router)
        public_router.include_router(client_public_router, tags=["Authentication"])

    # Include public router (always available)
    app.include_router(public_router, prefix=settings.API_PREFIX)

    return app


# Module-level app for direct OSS usage
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
