"""Tests for exceptions."""

from core.exceptions.base import (
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
    def test_app_exception_custom_values(self):
        exception = AppException(
            message="Custom error message",
            status_code=400,
            error_code="custom_error",
            details={"field": "value"},
        )

        assert exception.message == "Custom error message"
        assert exception.status_code == 400
        assert exception.error_code == "custom_error"
        assert exception.details == {"field": "value"}

    def test_app_exception_str_representation(self):
        exception = AppException(message="Test error")
        assert str(exception) == "Test error"

    def test_app_exception_get_default_error_code(self):
        exception = AppException(message="Test")
        assert exception._get_default_error_code() == "app"


class TestSpecificExceptions:
    def test_bad_request_exception(self):
        exception = BadRequestException(message="Bad request")
        assert exception.message == "Bad request"
        assert exception.status_code == 400
        assert exception.error_code == "bad_request"

    def test_unauthorized_exception(self):
        exception = UnauthorizedException(message="Unauthorized")
        assert exception.message == "Unauthorized"
        assert exception.status_code == 401
        assert exception.error_code == "unauthorized"

    def test_forbidden_exception(self):
        exception = ForbiddenException(message="Forbidden")
        assert exception.message == "Forbidden"
        assert exception.status_code == 403
        assert exception.error_code == "forbidden"

    def test_not_found_exception(self):
        exception = NotFoundException(message="Not found")
        assert exception.message == "Not found"
        assert exception.status_code == 404
        assert exception.error_code == "not_found"

    def test_conflict_exception(self):
        exception = ConflictException(message="Conflict")
        assert exception.message == "Conflict"
        assert exception.status_code == 409
        assert exception.error_code == "conflict"

    def test_validation_exception(self):
        exception = ValidationException(message="Validation failed")
        assert exception.message == "Validation failed"
        assert exception.status_code == 422
        assert exception.error_code == "validation"

    def test_internal_server_exception(self):
        exception = InternalServerException(message="Server error")
        assert exception.message == "Server error"
        assert exception.status_code == 500
        assert exception.error_code == "internal_server"

    def test_exception_with_custom_error_code(self):
        exception = BadRequestException(
            message="Custom", error_code="custom_bad_request"
        )
        assert exception.error_code == "custom_bad_request"
