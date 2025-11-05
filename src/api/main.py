"""Main FastAPI application."""

from fastapi import FastAPI

from leadr.config import settings

app = FastAPI(
    title="LEADR",
    description="LEADR is the cross-platform leadboard backend for indie game devs",
    version="0.1.0",
)

# Include routers


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
