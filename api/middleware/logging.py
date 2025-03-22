"""Request logging middleware for FastAPI."""

import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from config.logging_config import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""

    def __init__(
        self,
        app: FastAPI,
        log_request_body: bool = False,
        log_response_body: bool = False,
        exclude_paths: list = None,
    ):
        """
        Initialize request logging middleware.

        Args:
            app: FastAPI application
            log_request_body: Whether to log request bodies
            log_response_body: Whether to log response bodies
            exclude_paths: List of paths to exclude from logging
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json"]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request with logging.

        Args:
            request: FastAPI request
            call_next: Next middleware in the chain

        Returns:
            Response: FastAPI response
        """
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Start timer
        start_time = time.time()

        # Log request
        await self._log_request(request)

        # Process request
        try:
            response = await call_next(request)

            # Log response
            process_time = time.time() - start_time
            self._log_response(request, response, process_time)

            return response
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"- {type(e).__name__}: {str(e)} - {process_time:.4f}s"
            )
            raise

    async def _log_request(self, request: Request) -> None:
        """
        Log request details.

        Args:
            request: FastAPI request
        """
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Request: {request.method} {request.url.path} from {client_host}")

        # Log headers
        logger.debug(f"Request headers: {dict(request.headers)}")

        # Log request body if enabled
        if self.log_request_body:
            try:
                body = await request.body()
                if body:
                    logger.debug(f"Request body: {body.decode()}")
            except Exception as e:
                logger.warning(f"Failed to log request body: {str(e)}")

    def _log_response(
        self, request: Request, response: Response, process_time: float
    ) -> None:
        """
        Log response details.

        Args:
            request: FastAPI request
            response: FastAPI response
            process_time: Request processing time in seconds
        """
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - {process_time:.4f}s"
        )

        # Log headers
        logger.debug(f"Response headers: {dict(response.headers)}")

        # Log response body if enabled
        if self.log_response_body:
            try:
                body = response.body
                if body:
                    logger.debug(f"Response body: {body.decode()}")
            except Exception as e:
                logger.warning(f"Failed to log response body: {str(e)}")


def add_logging_middleware(
    app: FastAPI,
    log_request_body: bool = False,
    log_response_body: bool = False,
    exclude_paths: list = None,
) -> None:
    """
    Add request logging middleware to a FastAPI application.

    Args:
        app: FastAPI application
        log_request_body: Whether to log request bodies
        log_response_body: Whether to log response bodies
        exclude_paths: List of paths to exclude from logging
    """
    app.add_middleware(
        RequestLoggingMiddleware,
        log_request_body=log_request_body,
        log_response_body=log_response_body,
        exclude_paths=exclude_paths,
    )
