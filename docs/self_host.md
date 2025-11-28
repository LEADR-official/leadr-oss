# Self-Hosting LEADR

This guide covers deploying your own LEADR instance using Docker Compose.

## Prerequisites

- A ready cloud-hosting environment or your own server
- **Docker** and **Docker Compose** (v2.20+)
- A **domain name** with DNS control
- A **PostgreSQL 16+** database (cloud-hosted or self-managed)

For PostgreSQL, you can use any provider that gives you a standard connection string:

- Cloud: Supabase, Neon, AWS RDS, Google Cloud SQL, DigitalOcean
- Self-hosted: Your own PostgreSQL instance

## Quick Start

1. Clone the repository:

```bash
git clone https://github.com/LEADR-official/leadr-oss.git
cd leadr-oss
```

2. Create your environment file:

```bash
cp .env.example .env
```

3. Configure your `.env` file (see [Environment Variables](#environment-variables))

1. Start the stack:

```bash
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.selfhost.yml --env-file .env up -d
```

## Environment Variables

### Required

| Variable             | Description                                                      |
| -------------------- | ---------------------------------------------------------------- |
| `ENV`                | Environment name (e.g., `PROD`)                                  |
| `DB_HOST`            | PostgreSQL host (e.g., `db.example.com`)                         |
| `DB_PASSWORD`        | Database password                                                |
| `DB_NAME`            | Database name (default: `leadr`)                                 |
| `DB_USER`            | Database user (default: `leadr`)                                 |
| `DOMAIN`             | Your domain for routing (e.g., `example.com`)                    |
| `SUPERADMIN_API_KEY` | Admin API key - **must start with `ldr_`**                       |
| `JWT_SECRET`         | Secret for JWT signing - **generate a strong random string**     |
| `API_KEY_SECRET`     | Secret for API key hashing - **generate a strong random string** |

### Optional Variables

These have sensible defaults but can be customized:

| Variable                    | Default  | Description                           |
| --------------------------- | -------- | ------------------------------------- |
| `LEADR_IMAGE_TAG`           | `latest` | Docker image version (e.g., `v0.1.0`) |
| `DB_PORT`                   | `5432`   | PostgreSQL port                       |
| `DB_POOL_SIZE`              | `20`     | Database connection pool size         |
| `ACCESS_TOKEN_EXPIRY_HOURS` | `24`     | Device access token lifetime          |
| `REFRESH_TOKEN_EXPIRY_DAYS` | `30`     | Device refresh token lifetime         |
| `ANTICHEAT_ENABLED`         | `false`  | Enable anti-cheat checks              |

See `src/leadr/config.py` for the complete list of configuration options.

## Architecture

The self-hosted stack consists of:

```
                    ┌─────────────────────────────────┐
                    │           Caddy                 │
                    │    (Reverse Proxy + HTTPS)      │
                    └───────────┬─────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│       admin-api         │         │       client-api        │
│  api.admin.example.com  │         │    api.example.com      │
│                         │         │                         │
│  - Account management   │         │  - Score submissions    │
│  - Game configuration   │         │  - Leaderboard queries  │
│  - User management      │         │  - Device registration  │
└─────────────────────────┘         └─────────────────────────┘
              │                                   │
              └─────────────────┬─────────────────┘
                                │
                                ▼
                    ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐
                    │      PostgreSQL (not included)  │
                    └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘
```

- **admin-api**: Administrative endpoints for managing accounts, games, and users
- **client-api**: Public endpoints for game clients (score submission, leaderboards)
- **Caddy**: Automatic HTTPS with Let's Encrypt, routes traffic to appropriate API

## DNS Setup

Create two A records pointing to your server's IP address:

| Record                  | Type | Value              |
| ----------------------- | ---- | ------------------ |
| `api.example.com`       | A    | `<your-server-ip>` |
| `api.admin.example.com` | A    | `<your-server-ip>` |

Caddy will automatically obtain and renew TLS certificates from Let's Encrypt.

## Running the Stack

### Start

```bash
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.selfhost.yml --env-file .env up -d
```

### View Logs

```bash
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.selfhost.yml logs -f
```

### Stop

```bash
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.selfhost.yml down
```

### Verify Health

```bash
curl https://api.example.com/v1/health
curl https://api.admin.example.com/v1/health
```

Both should return a `200 OK` response.

## First Steps After Deploy

### Install the LEADR CLI

Download and install the CLI from the releases page:

```bash
curl -sSL https://github.com/LEADR-official/leadr-cli-releases/raw/main/install.sh | bash
```

Or download binaries directly from [github.com/LEADR-official/leadr-cli-releases](https://github.com/LEADR-official/leadr-cli-releases/releases).

### Configure Admin Authentication

1. **Verify the superadmin bootstrap**: On first startup, LEADR creates a superadmin account using your `SUPERADMIN_*` environment variables.

1. **Configure the CLI with your superadmin API key**:

```bash
leadr --host api.admin.example.com auth admin configure
```

Enter your `SUPERADMIN_API_KEY` when prompted.

### Create Your First Game

```bash
# Get your account ID (created during bootstrap)
leadr --host api.admin.example.com account get <account-id>

# Create a game
leadr --host api.admin.example.com game create \
  --account-id <account-id> \
  --name "My Game"
```

Run `leadr --help` to see all available commands.

## Optional Features

### GeoIP Auto-Labeling

LEADR can automatically extract geolocation (country, city, timezone) from player IP addresses using MaxMind GeoLite2 databases. This requires a free MaxMind account.

See the "GeoIP Auto-Labeling" section in `CLAUDE.md` for configuration details.

### Email Notifications

Email functionality (verification codes, notifications) requires Mailgun credentials:

- `MAILGUN_API_KEY`
- `MAILGUN_DOMAIN`

## Updating

To update to a newer version:

```bash
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.selfhost.yml pull
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.selfhost.yml up -d
```

Database migrations run automatically on startup when `RUN_MIGRATIONS=true` (default for selfhost).

## Troubleshooting

### Container won't start

Check logs for errors:

```bash
docker compose -f docker/docker-compose.base.yml -f docker/docker-compose.selfhost.yml logs admin-api
```

Common issues:

- Database connection failed: Verify `DB_HOST`, `DB_USER`, `DB_PASSWORD`
- Missing required env vars: Ensure all required variables are set

### Caddy certificate errors

- Ensure DNS records are correctly configured and propagated
- Verify ports 80 and 443 are accessible from the internet
- Check Caddy logs: `docker compose ... logs caddy`

### API returns 401/403

- Verify your API key starts with `ldr_`
- Ensure the `leadr-api-key` header is correctly spelled (lowercase)
