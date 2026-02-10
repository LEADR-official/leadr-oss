# LEADR - Cross-platform Leaderboards for Game Devs

![GitHub Tag](https://img.shields.io/github/v/tag/LEADR-Official/leadr-oss?color=FF007A)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/LEADR-Official/leadr-oss)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**Cross-platform leaderboards for game developers**. Add feature-rich leaderboards to your game on any platform, any engine, and unify all your players in one place. Open-source, with built-in anti-cheat and more, without trying to be your entire backend.

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
> Don't want the hassle of deploying it yourself? Get started for free at https://www.leadr.gg

## LEADR Cloud Features

- **Free Tier Available** - Get started in seconds at no cost, only pay when your game explodes
- **Beautiful Web Views** - Make your leaderboards more useful, with automatically generated, shareable, modern pages
- **More coming soon** - LEADR is under active development and [we've got lots planned](https://docs.leadr.gg/latest/roadmap/)...

## Quick Start

### LEADR Cloud

**Our fully managed and scalable hosted version of LEADR - just integrate LEADR via one of our SDKs.**

Download the LEADR app and run `leadr register` to get started:

#### Windows

Download the latest LEADR App version here: https://leadr.gg/download/windows

Double click the .exe and follow the instructions.

#### MacOS / Linux

```bash
curl -sSL https://leadr.gg/download/install.sh | bash
```

#### Manual install

Download binaries from the [Releases page](https://github.com/LEADR-official/leadr-releases/releases).

See the [LEADR docs](https://docs.leadr.gg/latest/) for more information and [quick start](https://docs.leadr.gg/latest/quick-start/) guides.

### Self host

Deploy our prebuilt & production-ready image to your preferred cloud host:

```plaintext
ghcr.io/LEADR-official/leadr-oss:latest
```

Check out the [self hosting docs](https://docs.leadr.gg/latest/api/self_host/) for more info.

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

LEADR uses PostgreSQL and supports both local development databases and managed PostgreSQL services (LEADR Cloud uses [Neon](https://neon.tech).

#### Using External PostgreSQL (Recommended for Production)

When using Neon's managed PostgreSQL, configure two endpoints:

```bash
# Pooled endpoint for connections using PgBouncer
DB_HOST=your.public.db.endpoint

# Direct endpoint used by migrations (bypasses PgBouncer)
DB_HOST_DIRECT=your.public.db.endpoint
```

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
