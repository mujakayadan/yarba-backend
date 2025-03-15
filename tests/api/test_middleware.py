"""Tests for API middleware."""

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from ...api.middleware.error_handler import add_error_handler_middleware
from ...api.middleware.logging import add_logging_middleware
from ...api.middleware.rate_limit import add_rate_limit_middleware


def test_error_handler_middleware():
    """Test error handler middleware."""
    # Create a test app with an endpoint that raises an exception
    app = FastAPI()

    @app.get("/test-error")
    async def test_error():
        raise ValueError("Test error")

    # Add error handler middleware
    add_error_handler_middleware(app, debug=True)

    # Create a test client
    client = TestClient(app)

    # Act
    response = client.get("/test-error")

    # Assert
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
    assert "error_code" in response.json()
    assert "timestamp" in response.json()


def test_logging_middleware():
    """Test logging middleware."""
    # Create a test app
    app = FastAPI()

    # Add logging middleware
    add_logging_middleware(app, log_request_body=True, log_response_body=True)

    # Add a test endpoint
    @app.get("/test-logging")
    async def test_logging():
        return {"message": "Test logging"}

    # Create a test client
    client = TestClient(app)

    # Act
    response = client.get("/test-logging")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "Test logging"}


def test_rate_limit_middleware():
    """Test rate limit middleware."""
    # Create a test app
    app = FastAPI()

    # Add rate limit middleware with a low limit
    add_rate_limit_middleware(app, rate_limit=2, window=60)

    # Add a test endpoint
    @app.get("/test-rate-limit")
    async def test_rate_limit():
        return {"message": "Test rate limit"}

    # Create a test client
    client = TestClient(app)

    # Act - First request should succeed
    response1 = client.get("/test-rate-limit")

    # Act - Second request should succeed
    response2 = client.get("/test-rate-limit")

    # Act - Third request should be rate limited
    response3 = client.get("/test-rate-limit")

    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 429
    assert "Too many requests" in response3.json()["detail"]


def test_middleware_order():
    """Test middleware execution order."""
    # Create a test app
    app = FastAPI()

    # Create a list to track middleware execution order
    execution_order = []

    # Create custom middleware for testing
    class TestMiddleware1(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            execution_order.append("middleware1_before")
            response = await call_next(request)
            execution_order.append("middleware1_after")
            return response

    class TestMiddleware2(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            execution_order.append("middleware2_before")
            response = await call_next(request)
            execution_order.append("middleware2_after")
            return response

    # Add middleware in specific order
    app.add_middleware(TestMiddleware1)
    app.add_middleware(TestMiddleware2)

    # Add a test endpoint
    @app.get("/test-order")
    async def test_order():
        execution_order.append("endpoint")
        return {"message": "Test order"}

    # Create a test client
    client = TestClient(app)

    # Act
    response = client.get("/test-order")

    # Assert
    assert response.status_code == 200
    assert execution_order == [
        "middleware2_before",
        "middleware1_before",
        "endpoint",
        "middleware1_after",
        "middleware2_after",
    ]
