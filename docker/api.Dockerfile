# From https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


# Then, use a final image without uv
FROM python:3.11-slim-bookworm

ARG VERSION=dev
LABEL org.opencontainers.image.title="leadr-api"
LABEL org.opencontainers.image.version="${VERSION}"

# Install curl for healthchecks
RUN apt-get update && \
     apt-get install -y --no-install-recommends curl gnupg && \
     curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg && \
     echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
     apt-get update && \
     apt-get install -y --no-install-recommends postgresql-client-16 && \
     rm -rf /var/lib/apt/lists/*

# Setup a non-root user
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

# Copy the application from the builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Use the non-root user to run our application
USER nonroot

# Use `/app` as the working directory
WORKDIR /app

# Expose the port the app runs on
EXPOSE 8000

# Run the FastAPI application by default
CMD ["./scripts/start.sh"]
