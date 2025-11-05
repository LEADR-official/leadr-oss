"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router as api_router
from leadr.common.database import engine
from leadr.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup: Database engine is already created at module import
    # The engine will establish connections as needed from the pool
    yield
    # Shutdown: Dispose of the database engine and close all connections
    await engine.dispose()


app = FastAPI(
    title="LEADR",
    description="LEADR is the cross-platform leadboard backend for indie game devs",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_PREFIX)

# Include domain routers
# Use settings.ENABLE_ADMIN_API & settings.ENABLE_CLIENT_API to control what routes are "on"


if __name__ == "__main__":
    from pathlib import Path

    import uvicorn
    import yaml

    # Load logging config from YAML file
    log_config_path = Path(__file__).parent / "logging.yaml"
    with log_config_path.open() as f:
        log_config = yaml.safe_load(f)

    # Substitute app and env values into the format strings
    for formatter in log_config["formatters"].values():
        if "fmt" in formatter:
            formatter["fmt"] = formatter["fmt"].format(app=settings.APP, env=settings.ENV)

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True, log_config=log_config)
