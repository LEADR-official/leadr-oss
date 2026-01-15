# Architectural Patterns

This document describes the architectural patterns and conventions used throughout the LEADR codebase.

## Table of Contents

1. [Domain-Driven Design Structure](#domain-driven-design-structure)
1. [Repository Pattern](#repository-pattern)
1. [Service Layer Pattern](#service-layer-pattern)
1. [Error Handling](#error-handling)
1. [API Schema Conversion](#api-schema-conversion)
1. [Route Organization](#route-organization)
1. [Soft Delete Pattern](#soft-delete-pattern)

## Domain-Driven Design Structure

The codebase follows Domain-Driven Design (DDD) principles with clear separation of concerns:

```
src/leadr/{domain}/
├── domain/          # Domain entities and business rules
│   ├── {entity}.py
├── adapters/        # Infrastructure adapters (ORM, external services)
│   ├── orm.py
├── services/        # Application services and repositories
│   ├── {entity}_service.py
│   ├── {entity}_repository.py
├── api/            # API layer (routes, schemas)
│   ├── routes.py
│   ├── schemas.py
```

### Layer Responsibilities

- **Domain**: Core business entities and rules. No dependencies on infrastructure.
- **Adapters**: Infrastructure concerns like database ORM models.
- **Services**: Application logic, orchestrates domain entities and repositories.
- **API**: HTTP concerns, request/response handling, delegates to services.

## Repository Pattern

Repositories provide a collection-like interface for accessing domain entities. All repositories extend `BaseRepository`.

### BaseRepository

Located in `src/leadr/common/base_repository.py`, provides standard CRUD operations:

```python
from leadr.common.base_repository import BaseRepository
from leadr.accounts.domain.account import Account
from leadr.accounts.adapters.orm import AccountORM

class AccountRepository(BaseRepository[Account, AccountORM]):
    def __init__(self, session: AsyncSession):
        super().__init__(Account, AccountORM, session)
```

### Standard Methods

- `get_by_id(entity_id: EntityID) -> T | None`
- `create(entity: T) -> T`
- `update(entity: T) -> T`
- `delete(entity_id: EntityID) -> None`
- `list_all() -> list[T]`

### Repository Mixins

For common query patterns, use repository mixins instead of duplicating code:

```python
from leadr.common.base_repository import BaseRepository, GetByFieldMixin

class AccountRepository(GetByFieldMixin[Account, AccountORM], BaseRepository[Account, AccountORM]):
    async def get_by_slug(self, slug: str) -> Account | None:
        return await self._get_by_field(AccountORM.slug, slug)
```

Available mixins:

- `GetByFieldMixin`: Provides `_get_by_field(field, value)` helper
- `ListByAccountMixin`: Provides `_list_by_account(account_id)` helper
- `CountByStatusMixin`: Provides `_count_where(conditions)` helper

### Custom Repository Methods

Add domain-specific query methods to repositories:

```python
class AccountRepository(BaseRepository[Account, AccountORM]):
    async def get_by_slug(self, slug: str) -> Account | None:
        """Get account by slug."""
        return await self._get_by_field(AccountORM.slug, slug)

    async def list_suspended(self) -> list[Account]:
        """List all suspended accounts."""
        stmt = select(self.orm_class).where(
            self.orm_class.status == "suspended",
            self.orm_class.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]
```

## Service Layer Pattern

Services contain application logic and orchestrate domain entities and repositories. All services extend `BaseService`.

### BaseService

Located in `src/leadr/common/services.py`, provides repository injection:

```python
from leadr.common.services import BaseService
from leadr.accounts.services.repositories import AccountRepository

class AccountService(BaseService[AccountRepository]):
    def __init__(self, session: AsyncSession):
        super().__init__(AccountRepository, session)
```

The service automatically creates the repository instance accessible via `self.repository`.

### Service Responsibilities

1. **Business Logic**: Implement domain-specific operations
1. **Orchestration**: Coordinate multiple repositories or entities
1. **Validation**: Validate business rules before persistence
1. **Error Handling**: Raise appropriate domain exceptions

### Service Method Examples

```python
class AccountService(BaseService[AccountRepository]):
    async def create_account(
        self,
        account_id: EntityID,
        name: str,
        slug: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> Account:
        """Create a new account."""
        # Check for duplicate slug
        existing = await self.repository.get_by_slug(slug)
        if existing:
            raise ValueError(f"Account with slug '{slug}' already exists")

        # Create entity
        account = Account(
            id=account_id,
            name=name,
            slug=slug,
            status=AccountStatus.ACTIVE,
            created_at=created_at,
            updated_at=updated_at,
        )

        return await self.repository.create(account)

    async def suspend_account(self, account_id: EntityID) -> Account:
        """Suspend an account."""
        account = await self.repository.get_by_id(account_id)
        if not account:
            raise EntityNotFoundError(f"Account {account_id} not found")

        account.suspend()
        return await self.repository.update(account)
```

### Service Layer Rules

- Services MUST NOT be accessed directly by routes in other domains
- Services MUST use repositories for all data access
- Services MUST raise `EntityNotFoundError` when entities are not found
- Services MUST validate business rules before persisting changes

## Error Handling

### Domain Exceptions

Use `EntityNotFoundError` for missing entities:

```python
from leadr.common.domain.exceptions import EntityNotFoundError

async def get_account(self, account_id: EntityID) -> Account:
    account = await self.repository.get_by_id(account_id)
    if not account:
        raise EntityNotFoundError(f"Account {account_id} not found")
    return account
```

### API Error Handling

Routes catch domain exceptions and convert to HTTP exceptions:

```python
from fastapi import HTTPException, status
from leadr.common.domain.exceptions import EntityNotFoundError

try:
    account = await service.get_account(entity_id)
except EntityNotFoundError as e:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Account not found"
    ) from e
```

### Foreign Key Violations

Catch `IntegrityError` for foreign key constraint violations:

```python
from sqlalchemy.exc import IntegrityError

try:
    api_key, plain_key = await service.create_api_key(
        account_id=account_id,
        name=request.name,
        expires_at=request.expires_at,
    )
except IntegrityError:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Account not found",
    ) from None
```

## API Schema Conversion

### Response Schema Pattern

API response schemas use `from_domain()` class methods for conversion:

```python
from pydantic import BaseModel
from leadr.accounts.domain.account import Account

class AccountResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, account: Account) -> "AccountResponse":
        """Convert domain entity to response schema."""
        return cls(
            id=account.id.value,
            name=account.name,
            slug=account.slug,
            status=account.status.value,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
```

### Usage in Routes

```python
@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, db: DatabaseSession) -> AccountResponse:
    service = AccountService(db)
    account = await service.get_account(EntityID.from_string(account_id))
    return AccountResponse.from_domain(account)
```

### Multiple Entity Responses

For responses that include related data from multiple entities:

```python
class CreateAPIKeyResponse(BaseModel):
    id: UUID
    account_id: UUID
    name: str
    key_prefix: str
    status: str
    created_at: datetime
    expires_at: datetime | None
    plain_key: str  # Only included on creation

    @classmethod
    def from_domain(cls, api_key: APIKey, plain_key: str) -> "CreateAPIKeyResponse":
        """Convert domain entity to creation response with plain key."""
        return cls(
            id=api_key.id.value,
            account_id=api_key.account_id.value,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            status=api_key.status.value,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            plain_key=plain_key,
        )
```

## Route Organization

### Domain-Based Routing

Routes are organized by domain in `src/leadr/{domain}/api/routes.py`:

```python
# src/leadr/accounts/api/routes.py
from fastapi import APIRouter

router = APIRouter()  # No prefix here

@router.post("/accounts", ...)
@router.get("/accounts/{account_id}", ...)
```

```python
# src/api/main.py
from leadr.accounts.api.routes import router as accounts_router
from leadr.auth.api.routes import router as auth_router

app.include_router(accounts_router, prefix=settings.API_PREFIX, tags=["Accounts"])
app.include_router(auth_router, prefix=settings.API_PREFIX)  # auth router has its own prefix
```

### Route Implementation Pattern

```python
@router.post("/accounts", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_account(request: AccountCreateRequest, db: DatabaseSession) -> AccountResponse:
    """Create a new account."""
    # 1. Create service
    service = AccountService(db)

    # 2. Get current timestamp
    now = datetime.now(UTC)

    # 3. Call service method
    account = await service.create_account(
        account_id=EntityID.generate(),
        name=request.name,
        slug=request.slug,
        created_at=now,
        updated_at=now,
    )

    # 4. Convert to response schema
    return AccountResponse.from_domain(account)
```

### Route Rules

- Routes MUST only call service methods, never repositories directly
- Routes MUST convert domain entities to response schemas using `from_domain()`
- Routes MUST handle service exceptions and convert to HTTP exceptions
- Routes MUST validate request data using Pydantic schemas

## Soft Delete Pattern

Soft deletes mark entities as deleted without removing them from the database.

### Domain Implementation

Entities have `deleted_at` field and `soft_delete()` method:

```python
from datetime import UTC, datetime

class Account(Entity):
    deleted_at: datetime | None = None

    def soft_delete(self) -> None:
        """Mark this account as deleted."""
        self.deleted_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
```

### Service Implementation

Services provide `delete_{entity}` methods:

```python
async def delete_account(self, account_id: EntityID) -> None:
    """Soft delete an account."""
    account = await self.repository.get_by_id(account_id)
    if not account:
        raise EntityNotFoundError(f"Account {account_id} not found")

    account.soft_delete()
    await self.repository.update(account)
```

### Route Implementation

Routes handle soft delete via PATCH with `deleted: true`:

```python
@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str, request: AccountUpdateRequest, db: DatabaseSession
) -> AccountResponse:
    service = AccountService(db)
    entity_id = EntityID.from_string(account_id)

    # Handle soft delete first
    if request.deleted is True:
        account = await service.get_account(entity_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        await service.delete_account(entity_id)
        # Return entity with 200 status (not 404)
        return AccountResponse.from_domain(account)

    # Handle other updates...
```

### Soft Delete Rules

- Soft deletes MUST return HTTP 200 with the entity, not HTTP 404
- Soft deletes MUST be idempotent (calling twice has same effect)
- Repositories MUST exclude soft-deleted entities from all queries by default
- Repositories MAY provide methods to include deleted entities if needed

## Testing Patterns

### Service Testing

Test services with real database transactions:

```python
@pytest.mark.asyncio
class TestAccountService:
    async def test_create_account(self, db_session: AsyncSession):
        service = AccountService(db_session)
        now = datetime.now(UTC)

        account = await service.create_account(
            account_id=EntityID.generate(),
            name="Test Corp",
            slug="test-corp",
            created_at=now,
            updated_at=now,
        )

        assert account.name == "Test Corp"
        assert account.status == AccountStatus.ACTIVE
```

### API Testing

Test routes through the HTTP client:

```python
@pytest.mark.asyncio
async def test_create_account_api(client: AsyncClient):
    response = await client.post(
        "/accounts",
        json={"name": "Test Corp", "slug": "test-corp"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Corp"
    assert data["status"] == "active"
```

### Test Organization

- Unit tests for domain entities in `tests/leadr/{domain}/domain/`
- Integration tests for services in `tests/leadr/{domain}/services/`
- API tests in `tests/api/{domain}/`
- Shared fixtures in `tests/conftest.py`
