"""Shared auth test helpers."""

from unittest.mock import MagicMock

from beanie import PydanticObjectId
from firebase_admin.auth import EmailAlreadyExistsError


def make_email_already_exists_error(*_args, **_kwargs) -> None:
    """Raise Firebase EmailAlreadyExistsError for AsyncMock side_effect."""
    raise EmailAlreadyExistsError(
        "The user with the provided email already exists (EMAIL_EXISTS).",
        Exception("EMAIL_EXISTS"),
        MagicMock(),
    )


def mock_user_record(
    *,
    email: str = "test@example.com",
    username: str = "testuser",
    firebase_uid: str = "firebase-test-uid",
    email_verified: bool = False,
) -> MagicMock:
    """Mock a persisted user without requiring Beanie initialization."""
    user = MagicMock()
    user.id = PydanticObjectId()
    user.email = email
    user.username = username
    user.firebase_uid = firebase_uid
    user.email_verified = email_verified
    user.is_active = True
    user.is_superuser = False
    user.auth_provider = "firebase.password"
    user.is_new_user = True
    user.current_setup_step = 1
    return user
