"""Rate limiting middleware for FastAPI."""

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import FastAPI, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config.logging_config import get_logger

logger = get_logger(__name__)

# In-memory store for rate limiting
# Format: {ip_address: [(timestamp1, count1), (timestamp2, count2), ...]}
RATE_LIMIT_STORE: dict[str, list] = defaultdict(list)

# Default rate limits
DEFAULT_RATE_LIMIT = 60  # requests per minute
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds

# PDF generation specific rate limits
PDF_RATE_LIMIT = 3  # requests per minute for PDF generation
PDF_RATE_LIMIT_WINDOW = 60  # seconds

# Route-specific rate limits
ROUTE_SPECIFIC_LIMITS = {
    # Pattern to match: (rate_limit, window)
    # More specific patterns should come before general ones
    "/api/v1/resumes/.*/pdf": (
        3,
        120,
    ),  # PDF generation endpoints - lower limit, longer window
    "/api/v1/resumes/": (30, 60),  # General resume endpoints
    "/api/v1/portfolio-websites/deployment-status": (
        60,
        60,
    ),  # Deployment status endpoint - allow more frequent polling but with limit
    "/api/v1/portfolio-websites/$": (
        60,
        60,
    ),  # Main portfolio website endpoint - allow more frequent polling but with limit
    "/api/v1/portfolio-websites/.*": (
        30,
        60,
    ),  # Other portfolio website endpoints
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI."""

    def __init__(
        self,
        app: FastAPI,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        window: int = DEFAULT_RATE_LIMIT_WINDOW,
        exclude_paths: list | None = None,
        get_key: Callable | None = None,
        route_specific_limits: dict[str, tuple[int, int]] | None = None,
    ):
        """Initialize rate limiting middleware.

        Args:
            app: FastAPI application
            rate_limit: Maximum number of requests per window
            window: Time window in seconds
            exclude_paths: List of paths to exclude from rate limiting
            get_key: Function to get the rate limit key (defaults to client IP)
            route_specific_limits: Dictionary of route patterns to (rate_limit, window) tuples
        """
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = window
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/"]
        self.get_key = get_key or self._get_client_ip
        if route_specific_limits is None:
            self.route_specific_limits = ROUTE_SPECIFIC_LIMITS
        else:
            self.route_specific_limits = route_specific_limits

        logger.info(
            f"Rate limiting middleware initialized: {rate_limit} requests per {window} seconds"
        )
        logger.info(f"Route-specific rate limits: {self.route_specific_limits}")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware in the chain

        Returns:
            Response: FastAPI response
        """
        # Skip rate limiting for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Get the appropriate rate limit and window for this path
        current_rate_limit = self.rate_limit
        current_window = self.window

        # Check for route-specific limits using regex patterns
        import re

        for pattern, (limit, window) in self.route_specific_limits.items():
            if re.search(pattern, request.url.path):
                current_rate_limit = limit
                current_window = window
                logger.debug(
                    f"Using route-specific limit for {request.url.path}: {limit} requests per {window} seconds"
                )
                break

        # Get rate limit key (usually client IP)
        key = f"{self.get_key(request)}:{request.url.path}"

        # Check rate limit
        is_rate_limited, headers = self._check_rate_limit(
            key, current_rate_limit, current_window
        )

        if is_rate_limited:
            logger.warning(f"Rate limit exceeded for {key} on {request.url.path}")
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to the response
        for header_name, header_value in headers.items():
            response.headers[header_name] = str(header_value)

        return response

    def _is_excluded_path(self, path: str) -> bool:
        for excluded in self.exclude_paths:
            if excluded == "/":
                if path == "/":
                    return True
            elif path.startswith(excluded):
                return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address from the request.

        Args:
            request: FastAPI request

        Returns:
            str: Client IP address
        """
        # Try to get the real IP from headers (if behind a proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Fall back to the client's direct IP
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(
        self, key: str, rate_limit: int, window: int
    ) -> tuple[bool, dict[str, str]]:
        """Check if the rate limit has been exceeded.

        Args:
            key: Rate limit key (usually client IP)
            rate_limit: Maximum number of requests per window for this route
            window: Time window in seconds for this route

        Returns:
            Tuple[bool, Dict[str, str]]: (is_rate_limited, headers)
        """
        current_time = time.time()
        time_window_start = current_time - window

        # Clean up old entries
        RATE_LIMIT_STORE[key] = [
            (timestamp, count)
            for timestamp, count in RATE_LIMIT_STORE[key]
            if timestamp > time_window_start
        ]

        # Count requests in the current window
        request_count = sum(count for _, count in RATE_LIMIT_STORE[key])

        # Update the store
        if not RATE_LIMIT_STORE[key]:
            RATE_LIMIT_STORE[key].append((current_time, 1))
        else:
            timestamp, count = RATE_LIMIT_STORE[key][-1]
            if timestamp == int(current_time):
                RATE_LIMIT_STORE[key][-1] = (timestamp, count + 1)
            else:
                RATE_LIMIT_STORE[key].append((int(current_time), 1))

        # Calculate remaining requests
        remaining = max(0, rate_limit - request_count)

        # Calculate reset time
        if RATE_LIMIT_STORE[key]:
            oldest_timestamp = min(timestamp for timestamp, _ in RATE_LIMIT_STORE[key])
            reset_time = int(oldest_timestamp + window - current_time)
        else:
            reset_time = window

        # Prepare headers
        headers = {
            "X-RateLimit-Limit": str(rate_limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        # Check if rate limit exceeded
        is_rate_limited = request_count >= rate_limit

        return is_rate_limited, headers


def add_rate_limit_middleware(
    app: FastAPI,
    rate_limit: int = DEFAULT_RATE_LIMIT,
    window: int = DEFAULT_RATE_LIMIT_WINDOW,
    exclude_paths: list | None = None,
    route_specific_limits: dict[str, tuple[int, int]] | None = None,
):
    """Add rate limiting middleware to a FastAPI application.

    Args:
        app: FastAPI application
        rate_limit: Maximum number of requests per window
        window: Time window in seconds
        exclude_paths: List of paths to exclude from rate limiting
        route_specific_limits: Dictionary of route patterns to (rate_limit, window) tuples
    """
    app.add_middleware(
        RateLimitMiddleware,
        rate_limit=rate_limit,
        window=window,
        exclude_paths=exclude_paths,
        route_specific_limits=route_specific_limits,
    )
