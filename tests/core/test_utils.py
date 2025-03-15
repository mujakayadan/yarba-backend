"""Tests for utility functions."""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from ...core.utils.jwt import create_access_token, decode_token
from ...core.utils.logging import get_logger
from ...core.utils.password import get_password_hash, verify_password


def test_password_hash_and_verify():
    """Test password hashing and verification."""
    # Arrange
    password = "TestPassword123!"

    # Act
    hashed_password = get_password_hash(password)
    is_valid = verify_password(password, hashed_password)
    is_invalid = verify_password("WrongPassword", hashed_password)

    # Assert
    assert hashed_password != password  # Hash should be different from original
    assert is_valid is True  # Correct password should verify
    assert is_invalid is False  # Wrong password should not verify


def test_password_hash_different_for_same_input():
    """Test that password hashing generates different hashes for the same input."""
    # Arrange
    password = "TestPassword123!"

    # Act
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Assert
    assert hash1 != hash2  # Hashes should be different due to salt


@pytest.mark.asyncio
async def test_create_and_decode_token():
    """Test creating and decoding JWT tokens."""
    # Arrange
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(minutes=15)

    # Mock the JWT_SECRET_KEY environment variable
    with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret_key"}):
        # Act
        token = await create_access_token(data, expires_delta)
        decoded_data = await decode_token(token)

        # Assert
        assert isinstance(token, str)
        assert decoded_data["sub"] == "test@example.com"
        assert "exp" in decoded_data  # Expiration time should be included


@pytest.mark.asyncio
async def test_token_expiration():
    """Test that expired tokens are rejected."""
    # Arrange
    data = {"sub": "test@example.com"}
    expires_delta = timedelta(seconds=-1)  # Token is already expired

    # Mock the JWT_SECRET_KEY environment variable
    with patch.dict(os.environ, {"JWT_SECRET_KEY": "test_secret_key"}):
        # Act
        token = await create_access_token(data, expires_delta)

        # Assert
        with pytest.raises(Exception) as excinfo:
            await decode_token(token)

        # Check that the error message contains something about expiration
        assert "expired" in str(excinfo.value).lower()


def test_get_logger():
    """Test that get_logger returns a logger with the correct name."""
    # Act
    logger = get_logger("test_module")

    # Assert
    assert logger.name == "test_module"
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
    assert hasattr(logger, "critical")


def test_logger_formatting():
    """Test logger formatting with a mock handler."""
    # Arrange
    import logging
    from io import StringIO

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)

    # Get logger and add our test handler
    logger = get_logger("test_format")
    logger.addHandler(handler)

    # Set a specific formatter to test
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Act
    logger.info("Test message")

    # Assert
    log_output = log_stream.getvalue()
    assert "INFO - Test message" in log_output
