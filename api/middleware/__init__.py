"""Middleware package for FastAPI."""

from fastapi import FastAPI

# Fix imports - use explicit imports from config modules
from config.settings import settings

from .auth import CurrentSuperuser, CurrentUser, get_current_user, verify_token
from .error_handler import add_error_handler_middleware
from .logging import add_logging_middleware
from .rate_limit import add_rate_limit_middleware


def setup_middlewares(app: FastAPI) -> None:
    """Set up all middlewares for the FastAPI application.

    Args:
        app: FastAPI application
    """
    # Add error handling middleware (should be first to catch all exceptions)
    add_error_handler_middleware(app, debug=settings.api.debug)

    # Add request logging middleware
    add_logging_middleware(
        app,
        log_request_body=False,  # Set to True to log request bodies (may contain sensitive data)
        log_response_body=False,  # Set to True to log response bodies (may be large)
    )

    # Add rate limiting middleware
    add_rate_limit_middleware(
        app,
        rate_limit=settings.api.rate_limit,
        window=settings.api.rate_limit_window,
        exclude_paths=[
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/api/v1/webhooks",
        ],
        route_specific_limits={
            # Pattern to match: (rate_limit, window)
            r"/api/v1/auth/password/(login|register)$": (10, 60),
            r"/api/v1/auth/password/(forgot-password|request-verification)$": (
                5,
                300,
            ),
            r"/api/v1/auth/password/(reset-password|confirm-verification|change-password)$": (
                10,
                300,
            ),
            r"/api/v1/auth/password/refresh$": (30, 60),
            r"/api/v1/auth/oauth/(google|apple)$": (20, 60),
            r"/api/v1/auth/oauth/nonce/(google|apple)$": (10, 60),
            "/api/v1/public/portfolio/chat": (10, 60),
            "/api/v1/resumes/": (
                settings.api.rate_limit,
                settings.api.rate_limit_window,
            ),
            "/api/v1/resumes/.*/pdf": (
                settings.api.pdf_rate_limit,
                settings.api.pdf_rate_limit_window,
            ),
            "/api/v1/cover-letters/.*/pdf": (
                settings.api.pdf_rate_limit,
                settings.api.pdf_rate_limit_window,
            ),
        },
    )


__all__ = [
    # Auth middleware
    "verify_token",
    "get_current_user",
    "CurrentUser",
    "CurrentSuperuser",
    # Middleware setup
    "setup_middlewares",
]
