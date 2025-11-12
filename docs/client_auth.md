# LEADR Client Authentication Guide

## Overview

LEADR provides secure authentication for game clients without requiring players to create accounts or remember passwords. If you use a LEADR SDK, then your game clients automatically authenticate anonymously using generated device IDs, so you don't need to worry about nonces and handshakes.

In case your interested, this guide explains how the authentication system works and how you could integrate it directly into your game without an SDKs help.

> [!TIP]
> 99% of users do not need to understand this process. This information is provided for transparency and to aid in SDK development.

______________________________________________________________________

## Quick Reference

### Required Headers

**All authenticated requests:**

```http
authorization: bearer <access_token>
```

**Token refresh:**

```http
authorization: bearer <refresh_token>
```

**Mutating operations only (POST, PATCH, DELETE):**

```http
authorization: bearer <access_token>
leadr-client-nonce: <nonce_value>
```

### Token Lifetimes

- **Access Token**: 15 minutes
- **Refresh Token**: 30 days
- **Nonce**: 60 seconds (single-use)

### Endpoints

| Endpoint                      | Method | Purpose           | Auth Required       |
| ----------------------------- | ------ | ----------------- | ------------------- |
| `/v1/client/sessions`         | POST   | Start new session | No                  |
| `/v1/client/sessions/refresh` | POST   | Refresh tokens    | Yes (refresh_token) |
| `/v1/client/nonce`            | GET    | Get nonce         | Yes (access_token)  |

______________________________________________________________________

## Key Terms

Before diving into the flows, here are the important concepts:

**Device**: A unique installation of your game. Each device gets a unique identifier that persists across game sessions.

**Session**: An authenticated connection between a device and LEADR. Sessions have access tokens that prove the device's identity.

**Access Token**: A short-lived credential (15 minutes) that the client includes with API requests. Think of it like a temporary badge that expires quickly.

**Refresh Token**: A long-lived credential (30 days) used to get new access tokens without starting a new session. Like a key card that lets you get new temporary badges.

**JWT (JSON Web Token)**: The format used for access and refresh tokens. It's a tamper-proof package containing the device's identity and expiration time.

**Nonce**: A single-use number issued by the server for making changes (like submitting scores). It prevents attackers from replaying captured requests.

**Replay Attack**: When an attacker captures a valid request and sends it again to perform unauthorized actions. Nonces prevent this.

______________________________________________________________________

## Security Goals

LEADR's authentication system protects against three main threats:

1. **Token Theft**: If someone steals an access token, it only works for 15 minutes. The refresh token allows legitimate users to continue their session.

1. **Replay Attacks**: Even with a valid token, attackers can't replay captured requests because each mutating operation requires a fresh, single-use nonce.

1. **Device Impersonation**: Tokens are tied to specific devices. A token from Device A won't work when pretending to be Device B.

______________________________________________________________________

## Phase 0: Starting a Session

This is the initial authentication step when the client starts.

### The Flow

```
Client                                    LEADR Server
  |                                           |
  |  POST /v1/client/sessions                |
  |  { game_id, device_id }                  |
  | ----------------------------------------> |
  |                                           |
  |                  Creates device record    |
  |                  Creates session          |
  |                  Generates tokens         |
  |                                           |
  |  { access_token, refresh_token,          |
  |    expires_in, device_id }               |
  | <---------------------------------------- |
  |                                           |
  | Store tokens securely                     |
  |                                           |
```

### Why This Design?

**Anonymous Authentication**: Players can start playing immediately without creating accounts. The device ID is all you need.

**No Secrets Required**: The client doesn't store API keys or passwords. The server issues tokens after verifying the game ID.

**Per-Game Isolation**: Each game has separate devices. A device in Game A can't access data from Game B.

### Inputs

The client generates or retrieves a device ID:

- First launch: Create a new UUID and save it permanently
- Subsequent launches: Load the existing device ID

### Client Action

Send session start request:

```http
POST /v1/client/sessions
content-type: application/json

{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

### Server Response

Server creates session and returns tokens:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 900,
  "device_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

The `expires_in` field shows access token lifetime in seconds (see Quick Reference: Token Lifetimes).

### Client Storage

Store the tokens securely:

- Use platform-specific secure storage (Keychain, PlayerPrefs, etc.)
- Never log tokens or send them to analytics

### Subsequent Requests

Include access_token in API requests:

```http
GET /v1/boards/abc123
authorization: bearer eyJhbGciOiJIUzI1NiIs...
```

### Common Errors

| Status | Error            | Meaning                             | Solution                                           |
| ------ | ---------------- | ----------------------------------- | -------------------------------------------------- |
| 404    | "Game not found" | The game_id doesn't exist in LEADR  | Double-check your game_id from the admin dashboard |
| 422    | Validation error | Missing or invalid device_id format | Ensure device_id is a valid UUID string            |

______________________________________________________________________

## Phase 1: Token Refresh

Access tokens expire after 15 minutes (see Quick Reference: Token Lifetimes). Instead of asking the client to re-authenticate, use the refresh token to get a new access token.

### The Flow

```
Client                                    LEADR Server
  |                                           |
  | API request with expired token            |
  | ----------------------------------------> |
  |                                           |
  |  401 Unauthorized                         |
  | <---------------------------------------- |
  |                                           |
  | POST /v1/client/sessions/refresh          |
  | authorization: bearer <refresh_token>     |
  | ----------------------------------------> |
  |                                           |
  |                  Validates refresh token  |
  |                  Generates new tokens     |
  |                  Rotates refresh token    |
  |                                           |
  |  { access_token, refresh_token,          |
  |    expires_in }                           |
  | <---------------------------------------- |
  |                                           |
  | Update stored tokens                      |
  | Retry original request                    |
  |                                           |
```

### Why Token Rotation?

When you refresh, both tokens change. On refresh the server issues a new access_token and a new refresh_token; you must atomically replace both tokens in storage (old refresh token is invalidated). This is a security feature:

- If an attacker steals your refresh token and uses it, you'll get an error next time you try to refresh
- You'll know something's wrong and can start a new session
- The attacker's stolen token becomes useless after one use

Think of it like getting a new key card every time you use it - if someone copies your card, their copy stops working as soon as you use yours.

### Inputs

An API request fails with 401 Unauthorized:

- This means the access token expired
- The response body might say "Token expired"

### Client Action

Request new tokens using refresh token:

```http
POST /v1/client/sessions/refresh
authorization: bearer eyJhbGciOiJIUzI1NiIs...
```

Use the refresh_token in the authorization header (not the access_token).

### Server Response

Server validates refresh token and issues new ones:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs... (NEW)",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs... (NEW, DIFFERENT)",
  "expires_in": 900
}
```

The `expires_in` field is in seconds (see Quick Reference: Token Lifetimes).

### Client Storage

Store BOTH new tokens atomically:

- The refresh token changed too! This is called "token rotation"
- The old refresh token won't work anymore
- Use atomic write to storage (all-or-nothing)

### Retry Logic

Retry the original request with the new access_token.

### Best Practices

**Proactive Refresh**: Don't wait for 401 errors. Refresh when `expires_in` approaches zero:

- Check expiration before each request
- Refresh if token expires in < 2 minutes
- This avoids failed requests

**Handle Refresh Failures**: If refresh fails (expired refresh token), start a new session:

- Refresh tokens last 30 days (see Quick Reference: Token Lifetimes)
- If the player hasn't played in 30+ days, they need a new session
- This is automatic and seamless to players

**Thread Safety**: Ensure only one refresh happens at a time:

- Multiple simultaneous requests might all try to refresh
- Lock the refresh operation to prevent race conditions
- Queue other requests until refresh completes

### Common Errors

| Status | Error                      | Meaning                               | Solution                                                 |
| ------ | -------------------------- | ------------------------------------- | -------------------------------------------------------- |
| 401    | "Invalid or expired token" | Refresh token expired or already used | Start a new session with POST /client/sessions           |
| 401    | "Token has been rotated"   | Someone else used this refresh token  | Possible token theft - start new session and investigate |

______________________________________________________________________

## Phase 2: Replay Protection with Nonces

For operations that change data (submitting scores, updating profiles), LEADR requires a nonce - a single-use ticket that proves the request is fresh.

### The Flow

```
Client                                    LEADR Server
  |                                           |
  | 1. GET /v1/client/nonce                   |
  |    authorization: bearer <access_token>   |
  | ----------------------------------------> |
  |                                           |
  |                  Issues fresh nonce       |
  |                  Stores in database       |
  |                                           |
  |  { nonce_value, expires_at }             |
  | <---------------------------------------- |
  |                                           |
  | 2. POST /v1/scores                        |
  |    authorization: bearer <access_token>   |
  |    leadr-client-nonce: <nonce_value>      |
  |    { score: 1000 }                        |
  | ----------------------------------------> |
  |                                           |
  |                  Validates nonce          |
  |                  Marks nonce as used      |
  |                  Processes request        |
  |                                           |
  |  { success: true }                        |
  | <---------------------------------------- |
  |                                           |
```

### Why Nonces Matter

Imagine an attacker captures a score submission request. Without nonces, they could replay it repeatedly to inflate a score. With nonces:

1. Each request needs a fresh nonce
1. Nonces are single-use
1. Replaying the captured request fails (nonce already used)
1. The attacker can't get new nonces without the access token

Think of nonces like scratch-off lottery tickets - each one can only be scratched once.

### Client Action 1: Request Nonce

Request a nonce before making a change:

```http
GET /v1/client/nonce
authorization: bearer eyJhbGciOiJIUzI1NiIs...
```

Use the access_token in the authorization header.

### Server Response

Server issues a fresh nonce:

```json
{
  "nonce_value": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "expires_at": "2025-11-12T15:30:00Z"
}
```

The nonce expires in 60 seconds (see Quick Reference: Token Lifetimes). Each nonce can only be used once. Each device gets its own nonces.

### Client Action 2: Use Nonce

Include the nonce in the mutation request:

```http
POST /v1/scores
authorization: bearer eyJhbGciOiJIUzI1NiIs...
leadr-client-nonce: a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d
content-type: application/json

{
  "board_id": "weekly-rankings",
  "score": 1000,
  "player_name": "Player1"
}
```

### Server Actions

Server validates and consumes the nonce:

- Checks nonce exists and belongs to the device
- Checks nonce hasn't been used yet
- Checks nonce hasn't expired
- Marks nonce as used (can't be used again)
- Processes the request

### Nonce Lifecycle

```
[Create] ----60 seconds----> [Expire]
   |
   |-- Use within 60s --> [Used] (permanent)
```

- **Created**: Server issues nonce, stores as PENDING
- **Used**: Client uses nonce, server marks as USED
- **Expired**: Nonce not used within 60 seconds, becomes invalid
- Used and expired nonces are kept for security auditing

### When to Get a Nonce

Get a fresh nonce for each mutating operation:

- Submitting a score: Get nonce
- Updating player profile: Get nonce
- Deleting data: Get nonce
- Fetching leaderboards: No nonce needed (read-only)
- Getting player stats: No nonce needed (read-only)

### Nonce Management Best Practices

**Don't Cache Nonces**: Always get a fresh nonce right before using it:

BAD:

- Get 10 nonces at once
- Use them throughout the game session
- Some will expire, some will fail

GOOD:

- Player triggers score submission
- Get nonce
- Submit score with nonce immediately

**Handle Concurrent Operations**: If submitting multiple scores simultaneously:

- Get separate nonces for each submission
- Don't reuse a nonce across requests
- Each operation needs its own nonce

**Retry Logic**: If nonce validation fails:

- Get a new nonce (don't retry with the same one)
- The old nonce is either expired, used, or invalid
- Fresh nonce = fresh start

### Common Errors

| Status | Error                                  | Meaning                             | Solution                                           |
| ------ | -------------------------------------- | ----------------------------------- | -------------------------------------------------- |
| 412    | "Nonce required"                       | No leadr-client-nonce header        | Add nonce header to request                        |
| 412    | "Invalid nonce"                        | Nonce doesn't exist or wrong format | Get a fresh nonce                                  |
| 412    | "Nonce expired"                        | Nonce older than 60 seconds         | Get a fresh nonce                                  |
| 412    | "Nonce already used"                   | Replaying a request                 | Get a fresh nonce, check for duplicate submissions |
| 412    | "Nonce does not belong to this device" | Using another device's nonce        | Each device must use its own nonces                |

______________________________________________________________________

## Complete Flow Example

Here's a typical game session from start to finish:

### Timeline: 30-Minute Play Session

```
00:00  |  Game Start
       |   > POST /client/sessions - Get access + refresh tokens
       |
00:05  |  Fetch Leaderboard
       |   > GET /boards/weekly (with access_token) - Success
       |
00:10  |  Submit Score
       |   > GET /client/nonce (with access_token) - Get nonce
       |   > POST /scores (with access_token + nonce) - Success
       |
00:15  |  Fetch Leaderboard Again
       |   > GET /boards/weekly (with access_token) - Success
       |
00:16  |  Access Token Expires
       |
00:17  |  Fetch Leaderboard
       |   > GET /boards/weekly (with expired access_token) - 401 Error
       |   > POST /sessions/refresh (with refresh_token) - New tokens
       |   > GET /boards/weekly (with NEW access_token) - Success
       |
00:25  |  Submit Another Score
       |   > GET /client/nonce (with access_token) - Get nonce
       |   > POST /scores (with access_token + nonce) - Success
       |
00:30  |  Game Exit
       |   > Tokens saved for next session
```

### What Happens Over Time

**Days 1-29**:

- Player starts game, uses saved refresh token
- Access token refreshed as needed every 15 minutes
- Smooth experience, no re-authentication

**Day 31** (after 30 days of not playing):

- Refresh token expired
- Game starts new session automatically
- Player doesn't notice anything
- New tokens last another 30 days

______________________________________________________________________

## Error Reference

### HTTP Status Codes

**401 Unauthorized**: Authentication problem

- Token missing, expired, or invalid
- Solution: Refresh token or start new session

**404 Not Found**: Resource doesn't exist

- Game ID, board ID, or device not found
- Solution: Check IDs are correct

**412 Precondition Failed**: Nonce problem

- Nonce missing, expired, used, or invalid
- Solution: Get fresh nonce and retry

**422 Unprocessable Entity**: Validation error

- Request body format is wrong
- Solution: Check API docs for correct format

### Common Error Messages

| Error Message              | What It Means                         | How to Fix                                       |
| -------------------------- | ------------------------------------- | ------------------------------------------------ |
| "Token expired"            | Access token past 15-minute limit     | Refresh using refresh_token                      |
| "Invalid or expired token" | Refresh token is old or invalid       | Start new session                                |
| "Game not found"           | game_id doesn't exist                 | Verify game_id from dashboard                    |
| "Nonce required"           | Mutation request missing nonce header | Get nonce, add to header                         |
| "Nonce expired"            | Nonce older than 60 seconds           | Get fresh nonce                                  |
| "Nonce already used"       | Trying to replay a request            | Get fresh nonce, check for duplicate submissions |

______________________________________________________________________

## Troubleshooting Guide

### "All my requests return 401"

**Cause**: Access token expired and refresh token is also expired/invalid

**Solution**:

1. Check if refresh token is stored
1. Try refreshing first
1. If refresh fails, start new session
1. Verify game hasn't been deleted or suspended

### "Nonce validation keeps failing"

**Cause**: Likely getting nonces too early or reusing them

**Solution**:

1. Get nonce immediately before use
1. Ensure no code is caching/reusing nonces
1. Check system clock is accurate (affects expiration)
1. Verify using leadr-client-nonce header (not authorization)

### "Refresh token rotation is confusing my code"

**Cause**: Not updating both tokens after refresh

**Solution**:

1. When refresh succeeds, store BOTH new tokens
1. Discard old refresh token completely
1. Use atomic write to storage (all-or-nothing)
1. Test with rapid refresh scenarios

### "Getting 412 errors on read requests"

**Cause**: Accidentally adding nonce header to read-only requests

**Solution**:

1. Only add nonce header to mutations (POST, PATCH, DELETE)
1. Read operations (GET) never need nonces
1. Check your HTTP client configuration

______________________________________________________________________

## Support

If you encounter issues not covered in this guide:

1. Check the main API documentation for endpoint details
1. Review your authentication implementation against this guide
1. Contact LEADR support with:
   - Your account ID & game ID
   - Device details (Steam + Windows 11, itch.io + Linux, Android, etc.)
   - Which LEADR SDK your game is using
   - Timestamps of failed requests (approximate is better than nothing)
   - Any HTTP status codes and error messages (never send actual tokens!)
