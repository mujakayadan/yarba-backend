"""User lookup and Yarba JWT helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from beanie import PydanticObjectId
from jwt.exceptions import PyJWTError as JWTError
from pydantic import EmailStr

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import NotFoundException, UnauthorizedException
from core.models.user import User
from core.repositories.user_repository import UserRepository

settings = Settings()


class AuthService:
    """User lookup and Yarba JWT helpers."""

    def __init__(self, user_repository: UserRepository | None = None):
        """Initialize the authentication service.

        Args:
            user_repository: Repository for accessing user data
        """
        self.user_repository = user_repository or UserRepository()
        self.logger = get_logger(self.__class__.__name__)

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Create a JWT access token.

        Args:
            data: Token data
            expires_delta: Token expiration time

        Returns:
            str: JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.auth.jwt_access_token_expire_minutes
            )

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithm=settings.auth.jwt_algorithm,
        )

        return str(encoded_jwt)

    async def get_user_by_id(self, user_id: PydanticObjectId) -> User:
        """Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User: User

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        return user

    async def get_user_by_email(self, email: EmailStr) -> User:
        """Get a user by email.

        Args:
            email: User email

        Returns:
            User: User

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_email(email)
        if not user:
            self.logger.warning(f"User not found: {email}")
            raise NotFoundException("User not found")

        return user

    async def update_user(
        self, user_id: PydanticObjectId, update_data: dict[str, Any]
    ) -> User:
        """Update a user.

        Args:
            user_id: User ID
            update_data: Data to update

        Returns:
            User: Updated user

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(user_id)

        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.now(UTC)

        try:
            await user.save()
            self.logger.info(f"User updated: {user_id}")
            return user
        except Exception as e:
            self.logger.error(f"Failed to update user: {str(e)}")
            raise NotFoundException("User not found")

    async def update_user_setup_progress(
        self,
        user_id: PydanticObjectId,
        current_setup_step: int | None,
        setup_completed: bool | None,
    ) -> User:
        """Update the user's setup progress.

        Args:
            user_id: The ID of the user to update.
            current_setup_step: The current setup step number.
            setup_completed: Boolean indicating if the setup is fully completed.

        Returns:
            The updated User object.

        Raises:
            NotFoundException: If the user is not found.
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(
                f"User not found with ID: {user_id} for setup progress update"
            )
            raise NotFoundException("User not found")

        update_data = {}
        if current_setup_step is not None:
            user.current_setup_step = current_setup_step
            update_data["current_setup_step"] = current_setup_step

        if setup_completed is not None:
            user.is_new_user = not setup_completed
            update_data["is_new_user"] = user.is_new_user
            if setup_completed:
                user.current_setup_step = 0
                update_data["current_setup_step"] = 0

        if not update_data:
            return user

        await user.save()
        self.logger.info(
            f"Updated setup progress for user {user_id}: step {user.current_setup_step}, new_user {user.is_new_user}"
        )
        return user

    async def verify_token(self, token: str) -> tuple[dict[str, Any], User]:
        """Verify a Yarba JWT and get the user.

        Args:
            token: JWT token

        Returns:
            Tuple[Dict, User]: Token payload and user

        Raises:
            UnauthorizedException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.auth.jwt_secret_key.get_secret_value(),
                algorithms=[settings.auth.jwt_algorithm],
            )

            email = payload.get("sub")
            if email is None:
                self.logger.warning("Token verification failed: Missing subject claim")
                raise UnauthorizedException("Invalid token")

            user = await self.get_user_by_email(email)
            return payload, user

        except JWTError as e:
            self.logger.warning(f"Token verification failed: {str(e)}")
            raise UnauthorizedException("Invalid token")

    async def deactivate_user(self, user_id: PydanticObjectId) -> User:
        """Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            User: Deactivated user

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(user_id)

        user.is_active = False
        user.updated_at = datetime.now(UTC)

        updated_user = await self.user_repository.update(user_id, user)
        if not updated_user:
            self.logger.error(f"Failed to deactivate user: {user_id}")
            raise NotFoundException("User not found or failed to update")

        self.logger.info(f"User deactivated: {user_id}")
        return updated_user
