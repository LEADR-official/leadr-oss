# Client API Quick Reference

A practical guide for integrating directly with the LEADR REST API. For in-depth concepts see:

- [Client Authentication Guide](api/client_auth.md).
- [API Reference](api/reference/index.md).

## Base URL

```
https://api.leadrcloud.com
```

Or,

```
https://your-leadr-instance.com
```

## Authentication

### 0. Generate a Device Fingerprint

The `client_fingerprint` identifies a device across sessions and helps LEADR fight cheaters. It is _never_ used for tracking players. It should be:

- **Stable**: Same value on each game launch
- **Unique-ish**: Different per device (collisions are acceptable)
- **SHA256 format**: 64 lowercase hex characters
- **NOT contain personal information**: To protect player privacy, don't use emails, IP addresses, social security numbers, or anything else that could be considered "personally identifiable information"

**Recommended approach:** Hash a combination of hardware/software identifiers available on your platform.

```
fingerprint = SHA256(platform + device_id + any_stable_identifier)
```

**Platform examples:**

| Platform | Suggested inputs                                                                                            |
| -------- | ----------------------------------------------------------------------------------------------------------- |
| Unity    | `SystemInfo.deviceUniqueIdentifier`, or combine `graphicsDeviceName` + `processorType` + `systemMemorySize` |
| Godot    | `OS.get_unique_id()`, or combine `OS.get_processor_name()` + `OS.get_video_adapter_driver_info()`           |
| Windows  | Combine CPU name, GPU name, total RAM, OS version, screen resolution                                        |
| macOS    | Combine `hw.model`, CPU brand, GPU name, screen resolution                                                  |
| Linux    | Combine `/proc/cpuinfo` model, GPU from `lspci`, total RAM, screen resolution                               |
| iOS      | `identifierForVendor` (or hardware model + screen scale + total memory)                                     |
| Android  | Combine `Build.MODEL` + `Build.MANUFACTURER` + screen density + total RAM                                   |
| Web      | Combine `navigator.hardwareConcurrency` + `screen.width` + `screen.height` + timezone + WebGL renderer      |

**Example (pseudocode):**

```
raw = "pc" + cpu_model + gpu_name + str(ram_gb) + screen_resolution
fingerprint = sha256(raw).hex()  # "a1b2c3d4..."
```

**Tips:**

- Store the fingerprint locally after first calculation for consistency
- If hardware changes, a new device record is created - no big deal
- Web fingerprints are less stable; consider a localStorage UUID as fallback

### 1. Start a Session

Authenticate your game client to get access tokens.

```http
POST /v1/client/sessions
Content-Type: application/json

{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_fingerprint": "a1b2c3d4e5f6...",
  "platform": "pc",
  "metadata": {"os": "Windows 11", "version": "1.0.0"}
}
```

| Field                | Required | Description                                        |
| -------------------- | -------- | -------------------------------------------------- |
| `game_id`            | Yes      | Your game's UUID from the admin dashboard          |
| `client_fingerprint` | Yes      | SHA256 device fingerprint (64 hex characters)      |
| `platform`           | No       | Platform identifier (e.g., "pc", "ios", "android") |
| `metadata`           | No       | Additional device info                             |

**Response:**

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900,
  "status": "active"
}
```

### 2. Refresh Tokens

Access tokens expire after 15 minutes. Use the refresh token to get new tokens.

```http
POST /v1/client/sessions/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900
}
```

Both tokens are rotated on each refresh. Store them atomically.

### 3. Get a Nonce (for mutations)

Mutating requests (POST, PATCH, DELETE) require a single-use nonce for replay protection.

```http
GET /v1/client/nonce
Authorization: Bearer <access_token>
```

**Response:**

```json
{
  "nonce_value": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "expires_at": "2025-01-15T12:30:00Z"
}
```

Nonces expire after 60 seconds and can only be used once.

### Token Lifetimes

| Token         | Lifetime   |
| ------------- | ---------- |
| Access Token  | 15 minutes |
| Refresh Token | 30 days    |
| Nonce         | 60 seconds |

______________________________________________________________________

## Boards

### List Boards

Retrieve available leaderboards for your game.

```http
GET /v1/client/boards
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter   | Description                                   |
| ----------- | --------------------------------------------- |
| `game_slug` | Filter by game slug                           |
| `slug`      | Filter by board slug (requires `game_slug`)   |
| `code`      | Filter by short code                          |
| `limit`     | Items per page (1-100, default: 20)           |
| `cursor`    | Pagination cursor                             |
| `sort`      | Sort order (e.g., `name:asc,created_at:desc`) |

**Response:**

```json
{
  "data": [
    {
      "id": "board-uuid",
      "name": "High Scores",
      "slug": "high-scores",
      "short_code": "WEEKLY-01",
      "sort_direction": "DESCENDING",
      "keep_strategy": "BEST_ONLY",
      "is_active": true,
      "unit": "points"
    }
  ],
  "pagination": {
    "count": 1,
    "has_next": false,
    "has_prev": false,
    "next_cursor": null,
    "prev_cursor": null
  }
}
```

______________________________________________________________________

## Scores

### Submit a Score

```http
POST /v1/client/scores
Authorization: Bearer <access_token>
leadr-client-nonce: <nonce_value>
Content-Type: application/json

{
  "board_id": "board-uuid",
  "player_name": "SpeedRunner42",
  "value": 12500,
  "value_display": "12,500 pts",
  "metadata": {"level": 5, "character": "ninja"}
}
```

| Field           | Required | Description                                |
| --------------- | -------- | ------------------------------------------ |
| `board_id`      | Yes      | UUID of the target leaderboard             |
| `player_name`   | Yes      | Display name for the player                |
| `value`         | Yes      | Numeric score value (used for sorting)     |
| `value_display` | No       | Formatted display string (e.g., "1:23.45") |
| `metadata`      | No       | Custom JSON data (max 1KB)                 |

**Response (201 Created):**

```json
{
  "id": "score-uuid",
  "account_id": "account-uuid",
  "game_id": "game-uuid",
  "board_id": "board-uuid",
  "player_name": "SpeedRunner42",
  "value": 12500,
  "value_display": "12,500 pts",
  "metadata": {"level": 5, "character": "ninja"},
  "created_at": "2025-01-15T12:00:00Z",
  "updated_at": "2025-01-15T12:00:00Z"
}
```

### List Scores

```http
GET /v1/client/scores
Authorization: Bearer <access_token>
```

**Query Parameters:**

| Parameter  | Description                                    |
| ---------- | ---------------------------------------------- |
| `board_id` | Filter by board UUID                           |
| `limit`    | Items per page (1-100, default: 20)            |
| `cursor`   | Pagination cursor                              |
| `sort`     | Sort order (e.g., `value:desc,created_at:asc`) |

**Valid sort fields:** `id`, `value`, `player_name`, `created_at`, `updated_at`

______________________________________________________________________

## Pagination

All list endpoints use cursor-based pagination.

```json
{
  "data": [...],
  "pagination": {
    "count": 20,
    "has_next": true,
    "has_prev": false,
    "next_cursor": "eyJwdiI6WzEwMDAsMTIzXX0=",
    "prev_cursor": null
  }
}
```

To fetch the next page, pass the cursor:

```http
GET /v1/client/scores?board_id=xxx&cursor=eyJwdiI6WzEwMDAsMTIzXX0=
```

______________________________________________________________________

## Error Reference

| Status | Meaning             | Common Causes                                                |
| ------ | ------------------- | ------------------------------------------------------------ |
| 401    | Unauthorized        | Token missing, expired, or invalid                           |
| 404    | Not Found           | Invalid game_id, board_id, or resource                       |
| 412    | Precondition Failed | Nonce missing, expired, or already used                      |
| 422    | Validation Error    | Invalid request body or parameters                           |
| 500    | Server Error        | Bugs and outages. Let us know: https://discord.gg/RMUukcAxSZ |

**Example error response:**

```json
{
  "detail": "Nonce expired"
}
```

______________________________________________________________________

## Quick Example: Submit a Score

```bash
# 1. Start session
curl -X POST https://api.leadr.gg/v1/client/sessions \
  -H "Content-Type: application/json" \
  -d '{"game_id": "YOUR_GAME_ID", "client_fingerprint": "sha256hash..."}'

# 2. Get nonce (use access_token from step 1)
curl https://api.leadr.gg/v1/client/nonce \
  -H "Authorization: Bearer ACCESS_TOKEN"

# 3. Submit score (use nonce from step 2)
curl -X POST https://api.leadr.gg/v1/client/scores \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "leadr-client-nonce: NONCE_VALUE" \
  -H "Content-Type: application/json" \
  -d '{"board_id": "BOARD_ID", "player_name": "Player1", "value": 1000}'
```

______________________________________________________________________

## Further Reading

- [Client Authentication Guide](client_auth.md) - Deep dive into auth concepts, token rotation, and security
- [Pagination Guide](pagination.md) - Detailed pagination patterns
