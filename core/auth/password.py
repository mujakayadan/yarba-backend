"""Password utility functions."""

import logging
from typing import Optional

from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from config.logging_config import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
        return pwd_context.verify(plain_password, hashed_password)
    except UnknownHashError:
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
    return pwd_context.hash(password)


def reset_user_password(user_obj: any, new_password: str) -> Optional[str]:
    """Reset a user's password.

    Args:
        user_obj: User object
        new_password: New password

    Returns:
        Optional[str]: New hashed password or None if error
    """
    try:
        new_hash = get_password_hash(new_password)
        return new_hash
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return None
