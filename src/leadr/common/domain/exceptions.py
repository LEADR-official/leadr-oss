"""Domain-specific exceptions for LEADR."""


class DomainError(Exception):
    """Base exception for all domain-level errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainError):
    """Raised when an entity cannot be found in the repository."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")


class InvalidEntityStateError(DomainError):
    """Raised when an entity is in an invalid state for the requested operation."""

    def __init__(self, entity_type: str, reason: str) -> None:
        self.entity_type = entity_type
        self.reason = reason
        super().__init__(f"Invalid {entity_type} state: {reason}")


class ValidationError(DomainError):
    """Raised when entity validation fails."""

    def __init__(self, entity_type: str, field: str, reason: str) -> None:
        self.entity_type = entity_type
        self.field = field
        self.reason = reason
        super().__init__(f"{entity_type}.{field}: {reason}")
