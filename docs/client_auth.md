# LEADR Client Authentication Guide

## Overview

LEADR provides secure authentication for game clients without requiring players to create accounts or remember passwords. Your game clients authenticate anonymously using device IDs, making it frictionless for players while maintaining security.

This guide explains how the authentication system works and how to integrate it into your game.

---

## Key Terms

Before diving into the flows, here are the important concepts:

**Device**: A unique installation of your game. Each device gets a unique identifier that persists across game sessions.

**Session**: An authenticated connection between a device and LEADR. Sessions have access tokens that prove the device's identity.

**Access Token**: A short-lived credential (15 minutes) that your game includes with API requests. Think of it like a temporary badge that expires quickly.

**Refresh Token**: A long-lived credential (30 days) used to get new access tokens without starting a new session. Like a key card that lets you get new temporary badges.

**JWT (JSON Web Token)**: The format used for access and refresh tokens. It's a tamper-proof package containing the device's identity and expiration time.

**Nonce**: A single-use number issued by the server for making changes (like submitting scores). It prevents attackers from replaying captured requests.

**Replay Attack**: When an attacker captures a valid request and sends it again to perform unauthorized actions. Nonces prevent this.

---

## Security Goals

LEADR's authentication system protects against three main threats:

1. **Token Theft**: If someone steals an access token, it only works for 15 minutes. The refresh token allows legitimate users to continue their session.

2. **Replay Attacks**: Even with a valid token, attackers can't replay captured requests because each mutating operation requires a fresh, single-use nonce.

3. **Device Impersonation**: Tokens are tied to specific devices. A token from Device A won't work when pretending to be Device B.

---

## Phase 0: Starting a Session

This is the initial authentication step when your game starts.

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

### Step by Step

1. **Your game generates or retrieves a device ID**
   - First launch: Create a new UUID and save it permanently
   - Subsequent launches: Load the existing device ID

2. **Send session start request**
   ```
   POST /v1/client/sessions
   Content-Type: application/json

   {
     "game_id": "550e8400-e29b-41d4-a716-446655440000",
     "device_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
   }
   ```

3. **Server creates session and returns tokens**
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIs...",
     "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
     "expires_in": 900,
     "device_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
   }
   ```

4. **Your game stores the tokens securely**
   - Use platform-specific secure storage (Keychain, PlayerPrefs, etc.)
   - Never log tokens or send them to analytics

5. **Include access_token in subsequent API requests**
   ```
   GET /v1/boards/abc123
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

### Why This Design?

**Anonymous Authentication**: Players can start playing immediately without creating accounts. The device ID is all you need.

**No Secrets Required**: Your game doesn't store API keys or passwords. The server issues tokens after verifying the game ID.

**Per-Game Isolation**: Each game has separate devices. A device in Game A can't access data from Game B.

### Common Errors

| Status | Error | Meaning | Solution |
|--------|-------|---------|----------|
| 404 | "Game not found" | The game_id doesn't exist in LEADR | Double-check your game_id from the admin dashboard |
| 422 | Validation error | Missing or invalid device_id format | Ensure device_id is a valid UUID string |

---

## Phase 1: Token Refresh

Access tokens expire after 15 minutes. Instead of asking your game to re-authenticate, use the refresh token to get a new access token.

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
  | Authorization: Bearer <refresh_token>     |
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

### Step by Step

1. **Your API request fails with 401 Unauthorized**
   - This means the access token expired
   - The response body might say "Token expired"

2. **Request new tokens using refresh token**
   ```
   POST /v1/client/sessions/refresh
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs... (refresh token)
   ```

3. **Server validates refresh token and issues new ones**
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIs... (NEW)",
     "refresh_token": "eyJhbGciOiJIUzI1NiIs... (NEW, DIFFERENT)",
     "expires_in": 900
   }
   ```

4. **Important: Store BOTH new tokens**
   - The refresh token changed too! This is called "token rotation"
   - Your old refresh token won't work anymore
   - This prevents token theft from working long-term

5. **Retry your original request with the new access token**

### Why Token Rotation?

When you refresh, both tokens change. This is a security feature:

- If an attacker steals your refresh token and uses it, you'll get an error next time you try to refresh
- You'll know something's wrong and can start a new session
- The attacker's stolen token becomes useless after one use

Think of it like getting a new key card every time you use it - if someone copies your card, their copy stops working as soon as you use yours.

### Best Practices

**Proactive Refresh**: Don't wait for 401 errors. Refresh when `expires_in` approaches zero:
- Check expiration before each request
- Refresh if token expires in < 2 minutes
- This avoids failed requests

**Handle Refresh Failures**: If refresh fails (expired refresh token), start a new session:
- Your refresh token lasts 30 days
- If the player hasn't played in 30+ days, they need a new session
- This is automatic and seamless to players

**Thread Safety**: Ensure only one refresh happens at a time:
- Multiple simultaneous requests might all try to refresh
- Lock the refresh operation to prevent race conditions
- Queue other requests until refresh completes

### Common Errors

| Status | Error | Meaning | Solution |
|--------|-------|---------|----------|
| 401 | "Invalid or expired token" | Refresh token expired or already used | Start a new session with POST /client/sessions |
| 401 | "Token has been rotated" | Someone else used this refresh token | Possible token theft - start new session and investigate |

---

## Phase 2: Replay Protection with Nonces

For operations that change data (submitting scores, updating profiles), LEADR requires a nonce - a single-use ticket that proves the request is fresh.

### The Flow

```
Client                                    LEADR Server
  |                                           |
  | 1. GET /v1/client/nonce                   |
  |    Authorization: Bearer <access_token>   |
  | ----------------------------------------> |
  |                                           |
  |                  Issues fresh nonce       |
  |                  Stores in database       |
  |                                           |
  |  { nonce_value, expires_at }             |
  | <---------------------------------------- |
  |                                           |
  | 2. POST /v1/scores                        |
  |    Authorization: Bearer <access_token>   |
  |    leadr-client-nonce: <nonce_value>     |
  |    { score: 1000 }                       |
  | ----------------------------------------> |
  |                                           |
  |                  Validates nonce          |
  |                  Marks nonce as used      |
  |                  Processes request        |
  |                                           |
  |  { success: true }                       |
  | <---------------------------------------- |
  |                                           |
```

### Step by Step

1. **Request a nonce before making a change**
   ```
   GET /v1/client/nonce
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   ```

2. **Server issues a fresh nonce**
   ```json
   {
     "nonce_value": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
     "expires_at": "2025-11-12T15:30:00Z"
   }
   ```
   - The nonce expires in 60 seconds
   - Each nonce can only be used once
   - Each device gets its own nonces

3. **Include the nonce in your mutation request**
   ```
   POST /v1/scores
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
   leadr-client-nonce: a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d
   Content-Type: application/json

   {
     "board_id": "weekly-rankings",
     "score": 1000,
     "player_name": "Player1"
   }
   ```

4. **Server validates and consumes the nonce**
   - Checks nonce exists and belongs to your device
   - Checks nonce hasn't been used yet
   - Checks nonce hasn't expired
   - Marks nonce as used (can't be used again)
   - Processes your request

### Why Nonces Matter

Imagine an attacker captures your score submission request. Without nonces, they could replay it repeatedly to inflate your score. With nonces:

1. Each request needs a fresh nonce
2. Nonces are single-use
3. Replaying the captured request fails (nonce already used)
4. The attacker can't get new nonces without your access token

Think of nonces like scratch-off lottery tickets - each one can only be scratched once.

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
-  Submitting a score: Get nonce
-  Updating player profile: Get nonce
-  Deleting data: Get nonce
- L Fetching leaderboards: No nonce needed (read-only)
- L Getting player stats: No nonce needed (read-only)

### Nonce Management Best Practices

**Don't Cache Nonces**: Always get a fresh nonce right before using it:
```
L BAD:
  - Get 10 nonces at once
  - Use them throughout the game session
  - Some will expire, some will fail

 GOOD:
  - Player triggers score submission
  - Get nonce
  - Submit score with nonce immediately
```

**Handle Concurrent Operations**: If submitting multiple scores simultaneously:
- Get separate nonces for each submission
- Don't reuse a nonce across requests
- Each operation needs its own nonce

**Retry Logic**: If nonce validation fails:
- Get a new nonce (don't retry with the same one)
- The old nonce is either expired, used, or invalid
- Fresh nonce = fresh start

### Common Errors

| Status | Error | Meaning | Solution |
|--------|-------|---------|----------|
| 412 | "Nonce required" | No leadr-client-nonce header | Add nonce header to request |
| 412 | "Invalid nonce" | Nonce doesn't exist or wrong format | Get a fresh nonce |
| 412 | "Nonce expired" | Nonce older than 60 seconds | Get a fresh nonce |
| 412 | "Nonce already used" | Replaying a request | Get a fresh nonce, check for duplicate submissions |
| 412 | "Nonce does not belong to this device" | Using another device's nonce | Each device must use its own nonces |

---

## Complete Flow Example

Here's a typical game session from start to finish:

### Timeline: 30-Minute Play Session

```
00:00  |  Game Start
       |   > POST /client/sessions ’ Get access + refresh tokens
       |
00:05  |  Fetch Leaderboard
       |   > GET /boards/weekly (with access_token) ’ Success
       |
00:10  |  Submit Score
       |   > GET /client/nonce (with access_token) ’ Get nonce
       |   > POST /scores (with access_token + nonce) ’ Success
       |
00:15  |  Fetch Leaderboard Again
       |   > GET /boards/weekly (with access_token) ’ Success
       |
00:16  |  Access Token Expires ð
       |
00:17  |  Fetch Leaderboard
       |   > GET /boards/weekly (with expired access_token) ’ 401 Error
       |   > POST /sessions/refresh (with refresh_token) ’ New tokens
       |   > GET /boards/weekly (with NEW access_token) ’ Success
       |
00:25  |  Submit Another Score
       |   > GET /client/nonce (with access_token) ’ Get nonce
       |   > POST /scores (with access_token + nonce) ’ Success
       |
00:30  |  Game Exit
       |   > Tokens saved for next session
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

---

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

| Error Message | What It Means | How to Fix |
|--------------|---------------|------------|
| "Token expired" | Access token past 15-minute limit | Refresh using refresh_token |
| "Invalid or expired token" | Refresh token is old or invalid | Start new session |
| "Game not found" | game_id doesn't exist | Verify game_id from dashboard |
| "Nonce required" | Mutation request missing nonce header | Get nonce, add to header |
| "Nonce expired" | Nonce older than 60 seconds | Get fresh nonce |
| "Nonce already used" | Trying to replay a request | Get fresh nonce, check for duplicate submissions |

---

## Best Practices Summary

### Token Management

1. **Store tokens securely**: Use platform-specific secure storage (Keychain on iOS, EncryptedSharedPreferences on Android)

2. **Refresh proactively**: Check expiration before each request, refresh if < 2 minutes remaining

3. **Handle refresh failures gracefully**: If refresh fails, start new session seamlessly

4. **Save refresh tokens**: Store refresh tokens between game sessions for seamless restarts

### Nonce Management

1. **Get nonces just-in-time**: Request nonce immediately before using it, not in advance

2. **One nonce per operation**: Each mutation needs its own fresh nonce

3. **Never cache or reuse nonces**: Always get a fresh nonce for each request

4. **Handle failures by getting fresh nonces**: If nonce validation fails, get a new one

### Security

1. **Never log tokens or nonces**: Don't send them to analytics or crash reporters

2. **Use HTTPS**: Always use secure connections to LEADR

3. **Handle token theft scenarios**: If refresh fails unexpectedly, consider it a security event

4. **Implement retry limits**: Don't retry failed nonce requests infinitely

### Performance

1. **Batch read operations**: Fetch multiple leaderboards at once (no nonces needed)

2. **Separate write operations**: Each score submission needs its own nonce

3. **Implement request queuing**: Queue requests that need nonces to avoid overwhelming the nonce endpoint

4. **Monitor token expiration**: Set timers to refresh proactively rather than reactively

---

## Troubleshooting Guide

### "All my requests return 401"

**Cause**: Access token expired and refresh token is also expired/invalid

**Solution**:
1. Check if refresh token is stored
2. Try refreshing first
3. If refresh fails, start new session
4. Verify game hasn't been deleted or suspended

### "Nonce validation keeps failing"

**Cause**: Likely getting nonces too early or reusing them

**Solution**:
1. Get nonce immediately before use
2. Ensure no code is caching/reusing nonces
3. Check system clock is accurate (affects expiration)
4. Verify using leadr-client-nonce header (not Authorization)

### "Refresh token rotation is confusing my code"

**Cause**: Not updating both tokens after refresh

**Solution**:
1. When refresh succeeds, store BOTH new tokens
2. Discard old refresh token completely
3. Use atomic write to storage (all-or-nothing)
4. Test with rapid refresh scenarios

### "Getting 412 errors on read requests"

**Cause**: Accidentally adding nonce header to read-only requests

**Solution**:
1. Only add nonce header to mutations (POST, PATCH, DELETE)
2. Read operations (GET) never need nonces
3. Check your HTTP client configuration

---

## Quick Reference

### Required Headers

**All authenticated requests:**
```
Authorization: Bearer <access_token>
```

**Mutating operations only (POST, PATCH, DELETE):**
```
Authorization: Bearer <access_token>
leadr-client-nonce: <nonce_value>
```

### Token Lifetimes

- **Access Token**: 15 minutes
- **Refresh Token**: 30 days
- **Nonce**: 60 seconds

### Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/v1/client/sessions` | POST | Start new session | No |
| `/v1/client/sessions/refresh` | POST | Refresh tokens | Yes (refresh token) |
| `/v1/client/nonce` | GET | Get nonce | Yes (access token) |

### When to Use What

| Operation | Access Token | Nonce | Example |
|-----------|--------------|-------|---------|
| Read data |  | L | GET /boards |
| Write data |  |  | POST /scores |
| Update data |  |  | PATCH /profile |
| Delete data |  |  | DELETE /account |
| Refresh tokens |  (refresh) | L | POST /sessions/refresh |
| Get nonce |  (access) | L | GET /nonce |

---

## Support

If you encounter issues not covered in this guide:

1. Check the main API documentation for endpoint details
2. Review your authentication implementation against this guide
3. Contact LEADR support with:
   - Your game ID
   - Device ID experiencing issues
   - Timestamps of failed requests
   - HTTP status codes and error messages (never send actual tokens!)
