# 🎮 LEADR - Lightweight Game Leaderboard API

> **LEADR is the cross-platform leadboard backend for indie game devs that turns any game into a social experience**

Whether you're building a retro arcade game, puzzle platformer, or competitive multiplayer experience, LEADR handles your leaderboard needs without the bloat and complexity - for any engine, any platform, any team.

## Game Features

- **🤯 Completely Cross Platform** - No need to individually integrate Steam, Unity Cloud, Google Play Services...
- **🥰 Developer Friendly** - The best docs. The clearest SDKs. Actual interest in the community
- **🔒 Anti-cheat by Default** - Secure and sophisticated server implementation to minimise and help triage abuse
- **🎯 We Do Leaderboards** - Different modes, levels, difficulties, geographies, units, sorting and more
- **📆 Seasons & Temporary Boards** - Automated leaderboards that reset or disable based on date & time
- **📊 More Than Scores** - Store ghost replays, custom metadata and user-generated content with every score
- **🔥 Beautiful Web Views** - Make your leaderboards a feature, with automatically generated, shareable, modern pages

## Software Features

- **🎉 Open-Source Core** - LEADR's cloud service is built on the very same software you're looking at right now
- **📦 Docker Ready** - Deploy to any cloud platform in minutes
- **💾 Zero Config** - Works out of the box
- **⚡ Lightning Fast** - Built to the latest industry standards by expert backend software developers (sadly we're better at making web apps than games)

> [!TIP]
> Don't want the hassle of deploying it yourself? Get started for free at https://leadr.gg

## Quick Start

Deploy our prebuilt & production-ready image to your preferred cloud host:

```plaintext
ghcr.io/LEADR-official/leadr:latest
```

Or try it out locally:

```bash
# Pull and run with Docker
docker run -d \
  -p 3000:3000 \
  -v leadr_data:/app/data \
  -e LEADR_API_KEY=your-secure-api-key \
  ghcr.io/LEADR-official/leadr:latest

# Test it's working
curl http://localhost:3000/health
```

**Required Environment Variables:**

- `LEADR_API_KEY` - Your API authentication key (required)

**Optional Configuration:**

- `DATABASE_URL` - Specify a different PostgreSQL database to connect to

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

- **Railway**: Deploy with one click using their Docker template
- **Fly.io**: Use `fly launch` with the included Dockerfile
- **Google Cloud Run**: Perfect for serverless deployments
- **DigitalOcean App Platform**: Simple container hosting
- **AWS ECS/Fargate**: For enterprise scale

Remember to set a strong `LEADR_API_KEY` environment variable

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
  -e LEADR_API_KEY=your_secret_key \
  leadr-api
```

### Database Management

...

### Documentation Generation

...

### Release Process

This project uses automated semantic versioning:

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
