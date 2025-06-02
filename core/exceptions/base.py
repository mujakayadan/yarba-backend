"""Base exception classes for the application."""

from typing import Any, Dict, Optional

from fastapi import status


class AppException(Exception):
    """Base exception class for application-specific exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize application exception.

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Error code for API clients
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self._get_default_error_code()
        self.details = details
        super().__init__(self.message)

    def _get_default_error_code(self) -> str:
        """
        Get default error code based on class name.

        Returns:
            str: Default error code
        """
        class_name = self.__class__.__name__
        if class_name.endswith("Exception"):
            class_name = class_name[:-9]  # Remove "Exception" suffix

        # Convert camel case to snake case
        import re

        error_code = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()

        return error_code


class BadRequestException(AppException):
    """Exception for bad request errors."""

    def __init__(
        self,
        message: str = "Bad request",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize bad request exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            details=details,
        )


class UnauthorizedException(AppException):
    """Exception for unauthorized access."""

    def __init__(
        self,
        message: str = "Unauthorized",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize unauthorized exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            details=details,
        )


class ForbiddenException(AppException):
    """Exception for forbidden access."""

    def __init__(
        self,
        message: str = "Forbidden",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize forbidden exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code,
            details=details,
        )


class NotFoundException(AppException):
    """Exception for not found resources."""

    def __init__(
        self,
        message: str = "Resource not found",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize not found exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code,
            details=details,
        )


class ConflictException(AppException):
    """Exception for resource conflicts."""

    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize conflict exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
            details=details,
        )


class ValidationException(AppException):
    """Exception for validation errors."""

    def __init__(
        self,
        message: str = "Validation error",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize validation exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=error_code,
            details=details,
        )


class OperationFailedException(AppException):
    """Exception for failed operations."""

    def __init__(
        self,
        message: str = "Operation failed",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize operation failed exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details,
        )


class InternalServerException(AppException):
    """Exception for internal server errors."""

    def __init__(
        self,
        message: str = "Internal server error",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize internal server exception."""
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details,
        )


class DeploymentException(AppException):
    """Exception raised when deployment operations fail."""

    def __init__(self, message: str = "Deployment operation failed"):
        """Initialize DeploymentException."""
        super().__init__(message)


class ValidationException(AppException):
    """Exception raised when validation fails."""

    def __init__(self, message: str = "Validation failed"):
        """Initialize ValidationException."""
        super().__init__(message)
