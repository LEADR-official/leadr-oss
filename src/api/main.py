"""Main FastAPI application."""

import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI

from api.routes import router as api_router
from leadr.common.database import engine
from leadr.config import settings

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
    yield
    # Shutdown: Dispose of the database engine and close all connections
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

# Always include shared routes (health check, root endpoint)
app.include_router(api_router, prefix=settings.API_PREFIX)

# Conditionally include admin domain routers
if settings.ENABLE_ADMIN_API:
    from leadr.accounts.api.routes import router as accounts_router

    app.include_router(accounts_router, prefix=settings.API_PREFIX, tags=["Accounts"])

# Conditionally include client domain routers
if settings.ENABLE_CLIENT_API:
    # TODO: Import and include client-specific domain routers here
    # Example:
    # from leadr.boards.api.client import router as boards_client_router
    # app.include_router(boards_client_router, prefix=settings.API_PREFIX)
    pass


if __name__ == "__main__":
    import uvicorn

    # Logging config already applied at module level
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
