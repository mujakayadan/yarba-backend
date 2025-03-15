"""Tests for exceptions."""

import pytest

from ...core.exceptions.base import (
    AppException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
    InternalServerException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)


class TestAppException:
    """Tests for AppException."""

    def test_app_exception_default_values(self):
        """Test AppException with default values."""
        # Act
        exception = AppException()

        # Assert
        assert exception.message == "An error occurred"
        assert exception.status_code == 500
        assert exception.error_code == "app_exception"
        assert exception.details is None

    def test_app_exception_custom_values(self):
        """Test AppException with custom values."""
        # Act
        exception = AppException(
            message="Custom error message",
            status_code=400,
            error_code="custom_error",
            details={"field": "value"},
        )

        # Assert
        assert exception.message == "Custom error message"
        assert exception.status_code == 400
        assert exception.error_code == "custom_error"
        assert exception.details == {"field": "value"}

    def test_app_exception_str_representation(self):
        """Test string representation of AppException."""
        # Act
        exception = AppException(message="Test error")

        # Assert
        assert str(exception) == "Test error"

    def test_app_exception_get_default_error_code(self):
        """Test _get_default_error_code method."""
        # Act
        error_code = AppException._get_default_error_code("TestErrorException")

        # Assert
        assert error_code == "test_error"


class TestSpecificExceptions:
    """Tests for specific exception classes."""

    def test_bad_request_exception(self):
        """Test BadRequestException."""
        # Act
        exception = BadRequestException(message="Bad request")

        # Assert
        assert exception.message == "Bad request"
        assert exception.status_code == 400
        assert exception.error_code == "bad_request"

    def test_unauthorized_exception(self):
        """Test UnauthorizedException."""
        # Act
        exception = UnauthorizedException(message="Unauthorized")

        # Assert
        assert exception.message == "Unauthorized"
        assert exception.status_code == 401
        assert exception.error_code == "unauthorized"

    def test_forbidden_exception(self):
        """Test ForbiddenException."""
        # Act
        exception = ForbiddenException(message="Forbidden")

        # Assert
        assert exception.message == "Forbidden"
        assert exception.status_code == 403
        assert exception.error_code == "forbidden"

    def test_not_found_exception(self):
        """Test NotFoundException."""
        # Act
        exception = NotFoundException(message="Not found")

        # Assert
        assert exception.message == "Not found"
        assert exception.status_code == 404
        assert exception.error_code == "not_found"

    def test_conflict_exception(self):
        """Test ConflictException."""
        # Act
        exception = ConflictException(message="Conflict")

        # Assert
        assert exception.message == "Conflict"
        assert exception.status_code == 409
        assert exception.error_code == "conflict"

    def test_validation_exception(self):
        """Test ValidationException."""
        # Act
        exception = ValidationException(message="Validation error")

        # Assert
        assert exception.message == "Validation error"
        assert exception.status_code == 422
        assert exception.error_code == "validation"

    def test_internal_server_exception(self):
        """Test InternalServerException."""
        # Act
        exception = InternalServerException(message="Internal server error")

        # Assert
        assert exception.message == "Internal server error"
        assert exception.status_code == 500
        assert exception.error_code == "internal_server"

    def test_exception_with_details(self):
        """Test exception with details."""
        # Act
        details = {"field": "username", "error": "Username already exists"}
        exception = ConflictException(
            message="User already exists",
            details=details,
        )

        # Assert
        assert exception.message == "User already exists"
        assert exception.status_code == 409
        assert exception.error_code == "conflict"
        assert exception.details == details

    def test_exception_with_custom_error_code(self):
        """Test exception with custom error code."""
        # Act
        exception = BadRequestException(
            message="Invalid input",
            error_code="invalid_input",
        )

        # Assert
        assert exception.message == "Invalid input"
        assert exception.status_code == 400
        assert exception.error_code == "invalid_input"
