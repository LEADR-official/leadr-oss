"""Tests for domain exceptions."""

import pytest

from leadr.common.domain.exceptions import (
    DomainError,
    EntityNotFoundError,
    InvalidEntityStateError,
    ValidationError,
)


class TestDomainError:
    """Tests for DomainError base exception."""

    def test_domain_error_creation(self) -> None:
        """Test creating a DomainError with a message."""
        error = DomainError("Something went wrong")
        assert error.message == "Something went wrong"
        assert str(error) == "Something went wrong"

    def test_domain_error_inheritance(self) -> None:
        """Test that DomainError inherits from Exception."""
        error = DomainError("Test error")
        assert isinstance(error, Exception)

    def test_domain_error_can_be_raised(self) -> None:
        """Test that DomainError can be raised and caught."""
        with pytest.raises(DomainError) as exc_info:
            raise DomainError("Test error")
        assert exc_info.value.message == "Test error"


class TestEntityNotFoundError:
    """Tests for EntityNotFoundError exception."""

    def test_entity_not_found_error_creation(self) -> None:
        """Test creating an EntityNotFoundError with entity type and ID."""
        error = EntityNotFoundError("Account", "123e4567-e89b-12d3-a456-426614174000")
        assert error.entity_type == "Account"
        assert error.entity_id == "123e4567-e89b-12d3-a456-426614174000"
        assert error.message == "Account not found: 123e4567-e89b-12d3-a456-426614174000"
        assert str(error) == "Account not found: 123e4567-e89b-12d3-a456-426614174000"

    def test_entity_not_found_error_inheritance(self) -> None:
        """Test that EntityNotFoundError inherits from DomainError."""
        error = EntityNotFoundError("User", "test-id")
        assert isinstance(error, DomainError)
        assert isinstance(error, Exception)

    def test_entity_not_found_error_can_be_raised(self) -> None:
        """Test that EntityNotFoundError can be raised and caught."""
        with pytest.raises(EntityNotFoundError) as exc_info:
            raise EntityNotFoundError("Game", "game-123")
        assert exc_info.value.entity_type == "Game"
        assert exc_info.value.entity_id == "game-123"

    def test_entity_not_found_error_caught_as_domain_error(self) -> None:
        """Test that EntityNotFoundError can be caught as DomainError."""
        with pytest.raises(DomainError) as exc_info:
            raise EntityNotFoundError("Board", "board-456")
        # Should be caught as DomainError but still be EntityNotFoundError
        assert isinstance(exc_info.value, EntityNotFoundError)


class TestInvalidEntityStateError:
    """Tests for InvalidEntityStateError exception."""

    def test_invalid_entity_state_error_creation(self) -> None:
        """Test creating an InvalidEntityStateError with entity type and reason."""
        error = InvalidEntityStateError("Account", "Cannot activate already active account")
        assert error.entity_type == "Account"
        assert error.reason == "Cannot activate already active account"
        assert error.message == "Invalid Account state: Cannot activate already active account"
        assert str(error) == "Invalid Account state: Cannot activate already active account"

    def test_invalid_entity_state_error_inheritance(self) -> None:
        """Test that InvalidEntityStateError inherits from DomainError."""
        error = InvalidEntityStateError("User", "Cannot delete active user")
        assert isinstance(error, DomainError)
        assert isinstance(error, Exception)

    def test_invalid_entity_state_error_can_be_raised(self) -> None:
        """Test that InvalidEntityStateError can be raised and caught."""
        with pytest.raises(InvalidEntityStateError) as exc_info:
            raise InvalidEntityStateError("Game", "Cannot modify archived game")
        assert exc_info.value.entity_type == "Game"
        assert exc_info.value.reason == "Cannot modify archived game"

    def test_invalid_entity_state_error_caught_as_domain_error(self) -> None:
        """Test that InvalidEntityStateError can be caught as DomainError."""
        with pytest.raises(DomainError) as exc_info:
            raise InvalidEntityStateError("Board", "Cannot update deleted board")
        assert isinstance(exc_info.value, InvalidEntityStateError)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_creation(self) -> None:
        """Test creating a ValidationError with entity type, field, and reason."""
        error = ValidationError("Account", "slug", "Must be lowercase alphanumeric")
        assert error.entity_type == "Account"
        assert error.field == "slug"
        assert error.reason == "Must be lowercase alphanumeric"
        assert error.message == "Account.slug: Must be lowercase alphanumeric"
        assert str(error) == "Account.slug: Must be lowercase alphanumeric"

    def test_validation_error_inheritance(self) -> None:
        """Test that ValidationError inherits from DomainError."""
        error = ValidationError("User", "email", "Invalid email format")
        assert isinstance(error, DomainError)
        assert isinstance(error, Exception)

    def test_validation_error_can_be_raised(self) -> None:
        """Test that ValidationError can be raised and caught."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Game", "name", "Cannot be empty")
        assert exc_info.value.entity_type == "Game"
        assert exc_info.value.field == "name"
        assert exc_info.value.reason == "Cannot be empty"

    def test_validation_error_caught_as_domain_error(self) -> None:
        """Test that ValidationError can be caught as DomainError."""
        with pytest.raises(DomainError) as exc_info:
            raise ValidationError("Board", "name", "Too long")
        assert isinstance(exc_info.value, ValidationError)


class TestExceptionHierarchy:
    """Tests for exception hierarchy and catching behavior."""

    def test_catch_all_domain_errors(self) -> None:
        """Test that all domain exceptions can be caught as DomainError."""
        exceptions = [
            EntityNotFoundError("Account", "123"),
            InvalidEntityStateError("User", "Invalid state"),
            ValidationError("Game", "name", "Invalid"),
        ]

        for exception in exceptions:
            with pytest.raises(DomainError):
                raise exception

    def test_specific_exception_catching(self) -> None:
        """Test that specific exceptions can be caught individually."""
        # EntityNotFoundError
        with pytest.raises(EntityNotFoundError):
            raise EntityNotFoundError("Account", "123")

        # InvalidEntityStateError
        with pytest.raises(InvalidEntityStateError):
            raise InvalidEntityStateError("User", "Invalid")

        # ValidationError
        with pytest.raises(ValidationError):
            raise ValidationError("Game", "name", "Invalid")
