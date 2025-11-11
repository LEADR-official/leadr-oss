"""Main FastAPI application."""

import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, FastAPI

from api.routes import router as api_router
from leadr.accounts.api.routes import router as accounts_router
from leadr.auth.api.client_routes import router as client_auth_router
from leadr.auth.api.routes import router as auth_router
from leadr.auth.dependencies import require_api_key
from leadr.boards.api.routes import router as boards_router
from leadr.boards.services.board_tasks import expire_boards, process_due_templates
from leadr.common.api.exceptions import entity_not_found_handler
from leadr.common.background_tasks import get_scheduler
from leadr.common.database import engine
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.config import settings
from leadr.games.api.routes import router as games_router
from leadr.scores.api.routes import router as scores_router

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

    # Register and start background tasks
    scheduler = get_scheduler()
    scheduler.add_task("process-due-templates", process_due_templates, interval_seconds=60)
    scheduler.add_task("expire-boards", expire_boards, interval_seconds=60)
    await scheduler.start()

    yield

    # Shutdown: Stop background tasks and dispose of the database engine
    await scheduler.stop()
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

# Include public router (always available)
app.include_router(public_router, prefix=settings.API_PREFIX)

# Include admin router only when Admin API is enabled
if settings.ENABLE_ADMIN_API:
    app.include_router(admin_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    # Logging config already applied at module level
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
