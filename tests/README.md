# Test Configuration

This directory contains the test suite for LEADR, configured for fully async operation with PostgreSQL.

## Fixtures

### Database Fixtures

1. **`test_database_name`** (session-scoped)

   - Generates a unique database name for the entire test session
   - Format: `leadr_test_{uuid}`

1. **`setup_test_database`** (session-scoped, auto-use)

   - Creates the test database at session start
   - Drops the test database at session end
   - Uses sync psycopg to avoid event loop issues

1. **`test_engine`** (function-scoped)

   - Creates an async SQLAlchemy engine for each test
   - Creates all tables (idempotent)
   - **Truncates all tables after test** for isolation
   - Disposes engine after test

1. **`db_session`** (function-scoped)

   - Provides an `AsyncSession` for database operations
   - Depends on `test_engine` (cleanup handled there)

1. **`client`** (function-scoped)

   - Provides an `AsyncClient` for making HTTP requests to the API
   - Overrides the `get_db` dependency to use the test session
   - Base URL: `http://testserver/v1`

## Usage

### Basic Database Test

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_something(db_session: AsyncSession):
    # Use db_session for database operations
    result = await db_session.execute(...)
    # Remember to commit explicitly!
    await db_session.commit()
```

### API Integration Test

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_endpoint(client: AsyncClient):
    response = await client.post("/v1/games", json={...})
    assert response.status_code == 201
```

## Key Features

- **Unique temporary database** per test run
- **Fast test isolation** via table truncation (not drop/create)
- **Fully async** using asyncpg and AsyncSession
- **Automatic cleanup** of database at session end
- **Safety checks** to prevent running tests in non-TEST environment

## Running Tests

```bash
# Run all tests
./scripts/test.sh

# Run specific test file
./scripts/test.sh tests/test_database.py

# Run specific test
./scripts/test.sh tests/test_database.py::test_name

# Run with verbose output
./scripts/test.sh -v
```

## Notes

- All tests must use `@pytest.mark.asyncio` decorator
- Database sessions do NOT auto-commit - call `await session.commit()` explicitly
- Tables are truncated between tests, not dropped/recreated (for speed)
- The test database is created once per test run and dropped at the end
- **Truncation happens in `test_engine` fixture** - this ensures cleanup occurs whether you use `db_session`, `client`, or `test_engine` directly
