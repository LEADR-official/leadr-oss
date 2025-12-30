# LEADR - Cross-platform Leaderboards for Game Devs

> **LEADR is the lightweight cross-platform leaderboard backend that turns any game into a social experience**

Whether you're building a retro arcade game, puzzle platformer, or competitive multiplayer experience, LEADR handles your leaderboard needs without the bloat and complexity - for any engine, any platform, any team.

## Game Features

- **Completely Cross Platform** - No need to individually integrate Steam, Unity Cloud, Google Play Services...
- **Developer Friendly** - The best docs. The clearest SDKs. Actual interest in the community
- **Anti-cheat by Default** - Secure and sophisticated server implementation to minimise and help triage abuse
- **We Do Leaderboards** - Different modes, levels, difficulties, geographies, units, sorting and more
- **Seasons & Temporary Boards** - Automated leaderboards that reset or disable based on date & time
- **More Than Just Scores** - Store ghost replay data, integrate your boards,

## Software Features

- **Open-Source Core** - LEADR's cloud service is built on this very same open-source core
- **Fully documented** - Clear, complete, developer-friendly docs
- **Docker Ready** - Deploy to any cloud platform in minutes
- **Zero Config** - Works out of the box
- **Secure & Scalable** - Built to the latest industry standards by expert backend software developers (sadly we're better at making web apps than games)

> [!TIP]
> Don't want the hassle of deploying it yourself? Get started for free at https://leadr.gg

## LEADR Cloud Features

- **Free Tier Available** - Get started in seconds at no cost, only pay when your game explodes
- **Beautiful Web Views** - Make your leaderboards more useful, with automatically generated, shareable, modern pages
- **More coming soon** - LEADR is under active development and [we've got lots planned](https://docs.leadr.gg/latest/roadmap/)...

## Quick Start

Deploy our prebuilt & production-ready image to your preferred cloud host:

```plaintext
ghcr.io/LEADR-official/leadr-oss:latest
```

Or try it out locally:

```bash
# Pull and run with Docker
docker run -d \
  -p 3000:3000 \
  -v leadr_data:/app/data \
  -e SUPERADMIN_API_KEY=ldr_your_secure_api_key \
  ghcr.io/LEADR-official/leadr:latest

# Test it's working
curl http://localhost:3000/v1/health
```

**Required Environment Variables:**

- `SUPERADMIN_API_KEY` - Superadmin authentication key for initial setup (must start with `ldr_`)
- `SUPERADMIN_EMAIL` - Email for superadmin user

Generate a secure API key:

```bash
# Generate a secure random API key
echo "ldr_$(openssl rand -base64 60 | tr -d '/+=')"
```

Store this in your `.env` file:

```bash
SUPERADMIN_API_KEY=ldr_your_generated_key_here
```

**Optional Configuration:**

- `DATABASE_URL` - Specify a different PostgreSQL database to connect to
- `SUPERADMIN_ACCOUNT_NAME` - Name of system account (default: LEADR)

## API Overview

...

### Pagination

All list endpoints return paginated responses:

```json
{
  "data": [...],
  "has_more": true,
  "next_cursor": "eyJpZCI6NDU2LCJzb3J0X3ZhbHVlIjoiMjAwMC4wIn0",
  "total_returned": 25,
  "page_size": 25
}
```

Use `next_cursor` as the `cursor` parameter for the next page.

## Cloud Deployment

LEADR works with any cloud platform that supports Docker:

- **Hetzner**: Europe-based cloud host - used by LEADR's cloud service
- **Railway**: Deploy with one click using their Docker template
- **Fly.io**: Use `fly launch` with the included Dockerfile
- **Google Cloud Run**: Perfect for serverless deployments
- **DigitalOcean App Platform**: Simple container hosting
- **AWS ECS/Fargate**: For enterprise scale

Remember to set a strong `SUPERADMIN_API_KEY` environment variable (must start with `ldr_`)

______________________________________________________________________

## Developer Documentation

### Local Development

...

### Docker Build

```bash
# Build image
docker buildx build -t leadr-api --load .

# Run locally
docker run -p 3000:3000 \
  -e SUPERADMIN_API_KEY=ldr_your_secret_key \
  leadr-api
```

### Database Management

LEADR uses PostgreSQL and supports both local development databases and managed PostgreSQL services like [Neon](https://neon.tech).

#### Environment Variables

| Variable         | Description                                             | Default                 |
| ---------------- | ------------------------------------------------------- | ----------------------- |
| `DB_HOST`        | PostgreSQL host                                         | `localhost`             |
| `DB_PORT`        | PostgreSQL port                                         | `5432`                  |
| `DB_NAME`        | Database name                                           | `leadr`                 |
| `DB_USER`        | Database user                                           | `leadr`                 |
| `DB_PASSWORD`    | Database password                                       | `leadr`                 |
| `DB_HOST_DIRECT` | Direct host for migrations (bypasses connection pooler) | Falls back to `DB_HOST` |

#### Using Neon (Recommended for Production)

When using Neon's managed PostgreSQL, configure two endpoints:

```bash
# Pooled endpoint for application connections (uses PgBouncer)
DB_HOST=ep-xxx-pooler.region.aws.neon.tech

# Direct endpoint for migrations (bypasses PgBouncer)
DB_HOST_DIRECT=ep-xxx.region.aws.neon.tech
```

**Connection behavior by environment:**

| Environment  | SSL         | Client Pooling      | Notes                              |
| ------------ | ----------- | ------------------- | ---------------------------------- |
| `DEV`/`TEST` | Disabled    | Enabled (QueuePool) | Local development                  |
| `PROD`       | verify-full | Disabled (NullPool) | Neon handles pooling via PgBouncer |

Migrations always use `DB_HOST_DIRECT` (if set) with `NullPool` to avoid issues with PgBouncer during schema changes.

#### Running Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Check migration status
uv run alembic current
```

### Documentation Generation

...

### Release Process

This project uses automated semantic versioning:

0. See what's changed: `git log <v tag>..HEAD && git diff <v tag> HEAD --stat`
1. Decide whether the release is a patch, minor or major version
1. Go to Actions → Release and Publish
1. Click "Run workflow"
1. The workflow will:
   - Analyze commits to determine version bump
   - Create a GitHub release
   - Build and push Docker images to GitHub Container Registry

### Contributing

We follow test-driven development:

0. Create a branch
1. Write tests first
1. Implement features
1. Ensure all tests pass
1. Ensure all CI checks pass
1. Make a PR

______________________________________________________________________

*Built with ❤️ for the indie game dev community*

![Umami pixel](https://cloud.umami.is/p/5cIK2JMht "Umami pixel")
