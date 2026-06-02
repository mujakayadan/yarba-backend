"""Tests for API middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from api.middleware.error_handler import add_error_handler_middleware
from api.middleware.logging import add_logging_middleware
from api.middleware.rate_limit import RATE_LIMIT_STORE, add_rate_limit_middleware


def test_error_handler_middleware():
    app = FastAPI()

    @app.get("/test-error")
    async def test_error():
        raise ValueError("Test error")

    add_error_handler_middleware(app, debug=True)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-error")

    assert response.status_code == 500
    body = response.json()
    assert body["status"] == "error"
    assert body["message"] == "An unexpected error occurred"
    assert body["error_code"] == "internal_server_error"
    assert "details" in body


def test_logging_middleware():
    app = FastAPI()
    add_logging_middleware(app, log_request_body=False, log_response_body=False)

    @app.get("/test-logging")
    async def test_logging():
        return {"message": "Test logging"}

    client = TestClient(app)
    response = client.get("/test-logging")

    assert response.status_code == 200
    assert response.json() == {"message": "Test logging"}


def test_rate_limit_middleware():
    RATE_LIMIT_STORE.clear()
    app = FastAPI()
    add_rate_limit_middleware(app, rate_limit=2, window=60, route_specific_limits={})

    @app.get("/test-rate-limit")
    async def test_rate_limit():
        return {"message": "Test rate limit"}

    client = TestClient(app)
    response1 = client.get("/test-rate-limit")
    response2 = client.get("/test-rate-limit")
    response3 = client.get("/test-rate-limit")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response3.status_code == 429
    assert "Rate limit exceeded" in response3.text


def test_middleware_order():
    app = FastAPI()
    execution_order = []

    class TestMiddleware1(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            execution_order.append("middleware1_before")
            response = await call_next(request)
            execution_order.append("middleware1_after")
            return response

    class TestMiddleware2(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            execution_order.append("middleware2_before")
            response = await call_next(request)
            execution_order.append("middleware2_after")
            return response

    app.add_middleware(TestMiddleware1)
    app.add_middleware(TestMiddleware2)

    @app.get("/test-order")
    async def test_order():
        execution_order.append("endpoint")
        return {"message": "Test order"}

    client = TestClient(app)
    response = client.get("/test-order")

    assert response.status_code == 200
    assert execution_order == [
        "middleware2_before",
        "middleware1_before",
        "endpoint",
        "middleware1_after",
        "middleware2_after",
    ]
