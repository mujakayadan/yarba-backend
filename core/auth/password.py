"""Password utility functions."""

from pwdlib import PasswordHash
from pwdlib import exceptions as pwd_exceptions
from pwdlib.hashers.bcrypt import BcryptHasher

from config.logging_config import get_logger

logger = get_logger(__name__)

# Bcrypt-only: verifies legacy passlib-generated $2b$ hashes in the database.
password_hasher = PasswordHash((BcryptHasher(),))


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
