"""Main FastAPI application."""

import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, FastAPI

from api.middleware import GeoIPMiddleware
from api.routes import router as api_router
from leadr.accounts.api.routes import router as accounts_router
from leadr.auth.api.client_routes import router as client_auth_router
from leadr.auth.api.device_routes import router as device_router
from leadr.auth.api.device_session_routes import router as device_session_router
from leadr.auth.api.routes import router as auth_router
from leadr.auth.bootstrap import ensure_superadmin_exists
from leadr.auth.dependencies import require_api_key
from leadr.auth.services.nonce_tasks import cleanup_expired_nonces
from leadr.boards.api.routes import router as boards_router
from leadr.boards.services.board_tasks import expire_boards, process_due_templates
from leadr.common.api.exceptions import entity_not_found_handler
from leadr.common.background_tasks import get_scheduler
from leadr.common.database import async_session_factory, engine
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.geoip import GeoIPService
from leadr.config import settings
from leadr.games.api.routes import router as games_router
from leadr.scores.api.routes import router as scores_router
from leadr.scores.api.score_flag_routes import router as score_flags_router
from leadr.scores.api.score_submission_meta_routes import router as score_submission_meta_router

# Configure logging from YAML file
log_config_path = Path(__file__).parent / "logging.yaml"
with log_config_path.open() as f:
    log_config = yaml.safe_load(f)

# Substitute app and env values into the format strings
for formatter in log_config["formatters"].values():
    if "fmt" in formatter:
        formatter["fmt"] = formatter["fmt"].format(app=settings.APP, env=settings.ENV)

# Apply logging configuration
logging.config.dictConfig(log_config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
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


# Determine API title and description based on enabled APIs
def get_api_title() -> str:
    """Get API title based on enabled APIs."""
    if settings.ENABLE_ADMIN_API and settings.ENABLE_CLIENT_API:
        return "LEADR - Admin & Client API"
    elif settings.ENABLE_ADMIN_API:
        return "LEADR - Admin API"
    elif settings.ENABLE_CLIENT_API:
        return "LEADR - Client API"
    else:
        raise Exception("One or both of ENABLE_ADMIN_API or ENABLE_CLIENT_API must be TRUE")


app = FastAPI(
    title=get_api_title(),
    description="LEADR is the cross-platform leaderboard backend for indie game devs",
    version="0.1.0",
    lifespan=lifespan,
)

# Register global exception handlers
app.add_exception_handler(EntityNotFoundError, entity_not_found_handler)

# Add GeoIP middleware (will use app.state.geoip_service from lifespan)
app.add_middleware(GeoIPMiddleware, dev_override_ip=settings.DEV_OVERRIDE_IP)

# Create public and admin routers with separate authentication requirements
public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_api_key)])

# Public routes - accessible without authentication
public_router.include_router(api_router)
public_router.include_router(client_auth_router, tags=["Client Authentication"])

# Admin routes - require API key authentication
admin_router.include_router(accounts_router, tags=["Accounts"])
admin_router.include_router(auth_router, tags=["API Keys"])
admin_router.include_router(games_router, tags=["Games"])
admin_router.include_router(boards_router, tags=["Boards"])
admin_router.include_router(scores_router, tags=["Scores"])
admin_router.include_router(score_flags_router, tags=["Score Flags"])
admin_router.include_router(score_submission_meta_router, tags=["Score Submission Metadata"])
admin_router.include_router(device_router, tags=["Devices"])
admin_router.include_router(device_session_router, tags=["Device Sessions"])

# Include public router (always available)
app.include_router(public_router, prefix=settings.API_PREFIX)

# Include admin router only when Admin API is enabled
if settings.ENABLE_ADMIN_API:
    app.include_router(admin_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    # Logging config already applied at module level
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
