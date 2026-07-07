"""Tests for utility functions."""

import logging
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock

import jwt
import pytest
from jwt.exceptions import ExpiredSignatureError

from config.logging_config import get_logger
from config.settings import settings
from core.auth.password import get_password_hash, verify_password
from core.services.auth_service import AuthService


def test_password_hash_and_verify():
    """Test password hashing and verification."""
    password = "TestPassword123!"
    hashed_password = get_password_hash(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password) is True
    assert verify_password("WrongPassword", hashed_password) is False


def test_password_hash_different_for_same_input():
    """Test that password hashing generates different hashes for the same input."""
    password = "TestPassword123!"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    assert hash1 != hash2


def test_create_and_decode_token():
    """Test creating and decoding JWT tokens via AuthService."""
    auth_service = AuthService(user_repository=MagicMock())
    data = {"sub": "test@example.com"}
    token = auth_service.create_access_token(data, timedelta(minutes=15))

    decoded = jwt.decode(
        token,
        settings.auth.jwt_secret_key.get_secret_value(),
        algorithms=[settings.auth.jwt_algorithm],
    )

    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded


def test_token_expiration():
    """Test that expired tokens are rejected."""
    auth_service = AuthService(user_repository=MagicMock())
    token = auth_service.create_access_token(
        {"sub": "test@example.com"},
        timedelta(seconds=-1),
    )

    with pytest.raises(ExpiredSignatureError):
        jwt.decode(
            token,
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithms=[settings.auth.jwt_algorithm],
        )


def test_get_logger():
    """Test that get_logger returns a logger with the correct name."""
    logger = get_logger("test_module")

    assert logger.name == "test_module"
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
    assert hasattr(logger, "critical")


def test_logger_formatting():
    """Test logger formatting with a mock handler."""
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = get_logger("test_format")
    logger.addHandler(handler)
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

    logger.info("Test message")

    assert "INFO - Test message" in log_stream.getvalue()
