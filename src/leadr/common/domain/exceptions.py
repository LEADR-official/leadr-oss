"""Domain-specific exceptions for LEADR."""


class DomainError(Exception):
    """Base exception for all domain-level errors.

    All custom domain exceptions should inherit from this base class.
    This allows catching all domain errors with a single except clause.

    Args:
        message: Human-readable error message.

    Example:
        >>> try:
        ...     raise DomainError("Something went wrong")
        ... except DomainError as e:
        ...     print(e.message)
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainError):
    """Raised when an entity cannot be found in the repository.

    This exception is raised by repository queries when an entity with
    the specified ID does not exist in the database.

    Args:
        entity_type: Name of the entity type (e.g., "Account", "User").
        entity_id: The ID that was not found.

    Example:
        >>> raise EntityNotFoundError("Account", "123e4567-e89b-12d3-a456-426614174000")
        EntityNotFoundError: Account not found: 123e4567-e89b-12d3-a456-426614174000
    """

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")


class InvalidEntityStateError(DomainError):
    """Raised when an entity is in an invalid state for the requested operation.

    Use this exception when business rules prevent an operation due to the
    current state of an entity. For example, activating an already-active account,
    or modifying a deleted entity.

    Args:
        entity_type: Name of the entity type (e.g., "Account", "User").
        reason: Explanation of why the state is invalid.

    Example:
        >>> raise InvalidEntityStateError("Account", "Cannot activate already active account")
        InvalidEntityStateError: Invalid Account state: Cannot activate already active account
    """

    def __init__(self, entity_type: str, reason: str) -> None:
        self.entity_type = entity_type
        self.reason = reason
        super().__init__(f"Invalid {entity_type} state: {reason}")


class ValidationError(DomainError):
    """Raised when entity validation fails.

    Use this exception when field-level validation fails, such as invalid
    format, out-of-range values, or constraint violations.

    Args:
        entity_type: Name of the entity type (e.g., "Account", "User").
        field: Name of the field that failed validation.
        reason: Explanation of why validation failed.

    Example:
        >>> raise ValidationError("Account", "slug", "Must be lowercase alphanumeric")
        ValidationError: Account.slug: Must be lowercase alphanumeric
    """

    def __init__(self, entity_type: str, field: str, reason: str) -> None:
        self.entity_type = entity_type
        self.field = field
        self.reason = reason
        super().__init__(f"{entity_type}.{field}: {reason}")
