"""Error handling middleware for FastAPI."""

import traceback
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config import settings
from config.logging_config import get_logger
from core.exceptions.base import AppException

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and exceptions."""

    def __init__(
        self,
        app: FastAPI,
        debug: bool = False,
    ):
        """
        Initialize error handling middleware.

        Args:
            app: FastAPI application
            debug: Whether to include debug information in error responses
        """
        super().__init__(app)
        self.debug = debug

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request with error handling.

        Args:
            request: FastAPI request
            call_next: Next middleware in the chain

        Returns:
            Response: FastAPI response
        """
        try:
            return await call_next(request)
        except AppException as e:
            # Handle application-specific exceptions
            return self._handle_app_exception(e, request)
        except Exception as e:
            # Handle unexpected exceptions
            return await self._handle_unexpected_exception(e, request)

    def _handle_app_exception(
        self, exc: AppException, request: Request
    ) -> JSONResponse:
        """
        Handle application-specific exceptions.

        Args:
            exc: Application exception
            request: FastAPI request

        Returns:
            JSONResponse: Error response
        """
        logger.warning(
            f"Application exception: {type(exc).__name__} - {str(exc)} - "
            f"{request.method} {request.url.path}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=self._format_error_response(
                status_code=exc.status_code,
                message=str(exc),
                error_code=exc.error_code,
                details=exc.details,
            ),
        )

    async def _handle_unexpected_exception(
        self, exc: Exception, request: Request
    ) -> JSONResponse:
        """
        Handle unexpected exceptions.

        Args:
            exc: Unexpected exception
            request: FastAPI request

        Returns:
            JSONResponse: Error response
        """
        # Log the exception with traceback
        logger.error(
            f"Unexpected exception: {type(exc).__name__} - {str(exc)} - "
            f"{request.method} {request.url.path}"
        )
        logger.error(traceback.format_exc())

        # Prepare error response
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "An unexpected error occurred"

        # Include exception details in debug mode
        details = None
        if self.debug:
            details = {
                "exception": str(exc),
                "traceback": traceback.format_exc().split("\n"),
            }

        return JSONResponse(
            status_code=status_code,
            content=self._format_error_response(
                status_code=status_code,
                message=message,
                error_code="internal_server_error",
                details=details,
            ),
        )

    def _format_error_response(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format error response.

        Args:
            status_code: HTTP status code
            message: Error message
            error_code: Error code
            details: Additional error details

        Returns:
            Dict[str, Any]: Formatted error response
        """
        response = {
            "status": "error",
            "message": message,
        }

        if error_code:
            response["error_code"] = error_code

        if details and (self.debug or settings.environment != "production"):
            response["details"] = details

        return response


def add_error_handler_middleware(app: FastAPI, debug: bool = False) -> None:
    """
    Add error handling middleware to a FastAPI application.

    Args:
        app: FastAPI application
        debug: Whether to include debug information in error responses
    """
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=debug,
    )
