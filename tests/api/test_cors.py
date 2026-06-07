"""Tests for CORS headers on all responses including error paths."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api.middleware import setup_middlewares
from core.exceptions.base import BadRequestException, ConflictException

TEST_CORS_ORIGIN = "https://www.yarba.app"


def _build_app_with_production_cors_order() -> FastAPI:
    """Mirror api.main middleware order: inner middlewares first, CORS outermost."""
    app = FastAPI()
    setup_middlewares(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[TEST_CORS_ORIGIN, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/test-bad-request")
    async def test_bad_request():
        raise BadRequestException(message="Bad request test")

    @app.post("/test-conflict")
    async def test_conflict():
        raise ConflictException(
            message="Conflict test",
            error_code="email_already_registered",
        )

    return app


def test_cors_headers_on_bad_request_error():
    app = _build_app_with_production_cors_order()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/test-bad-request",
        headers={"Origin": TEST_CORS_ORIGIN},
    )

    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") == TEST_CORS_ORIGIN
    body = response.json()
    assert body["status"] == "error"
    assert body["message"] == "Bad request test"


def test_cors_headers_on_conflict_error():
    app = _build_app_with_production_cors_order()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/test-conflict",
        headers={"Origin": TEST_CORS_ORIGIN},
    )

    assert response.status_code == 409
    assert response.headers.get("access-control-allow-origin") == TEST_CORS_ORIGIN
    body = response.json()
    assert body["error_code"] == "email_already_registered"
