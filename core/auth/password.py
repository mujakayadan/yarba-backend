"""Password utility functions."""

import re

from pwdlib import PasswordHash
from pwdlib import exceptions as pwd_exceptions
from pwdlib.hashers.bcrypt import BcryptHasher

from config.logging_config import get_logger

logger = get_logger(__name__)

# Bcrypt-only: verifies legacy passlib-generated $2b$ hashes in the database.
password_hasher = PasswordHash((BcryptHasher(),))
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d.@$!%*?&#]{8,64}$"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches hash, False otherwise
    """
    if not hashed_password:
        logger.warning("Empty hashed password provided for verification")
        return False

    try:
        return password_hasher.verify(plain_password, hashed_password)
    except pwd_exceptions.UnknownHashError:
        logger.error(
            f"Unknown hash format detected. Hash might be invalid or corrupted. Length: {len(hashed_password)}"
        )
        return False
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """Generate a password hash.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return password_hasher.hash(password)


def validate_password_policy(password: str) -> str:
    """Validate the shared native and Firebase password policy."""
    if not PASSWORD_PATTERN.fullmatch(password):
        raise ValueError(
            "Password must be 8-64 characters and contain at least one uppercase "
            "letter, one lowercase letter, and one number"
        )
    return password
