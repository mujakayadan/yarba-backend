"""User repository implementation."""

from datetime import datetime, timezone
from typing import List, Optional

from beanie import PydanticObjectId
from pydantic import EmailStr

from ..models.portfolio import Portfolio
from ..models.profile import Profile
from ..models.resume import Resume
from ..models.user import User
from .base_repository import BeanieRepository


class UserRepository(BeanieRepository[User]):
    """Repository for User documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(User)

    async def get_by_email(self, email: EmailStr) -> Optional[User]:
        """
        Get a user by email.

        Args:
            email: User email

        Returns:
            Optional[User]: User if found, None otherwise
        """
        return await User.find_one({"email": email})

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Args:
            username: Username

        Returns:
            Optional[User]: User if found, None otherwise
        """
        return await User.find_one({"username": username})

    async def get_by_id(self, user_id: PydanticObjectId) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            Optional[User]: User if found, None otherwise
        """
        return await User.find_one({"_id": user_id})

    async def get_active_users(self) -> List[User]:
        """
        Get all active users.

        Returns:
            List[User]: List of active users
        """
        return await User.find({"is_active": True}).to_list()

    async def get_superusers(self) -> List[User]:
        """
        Get all superusers.

        Returns:
            List[User]: List of superusers
        """
        return await User.find({"is_superuser": True}).to_list()

    async def get_profiles(self, user_id: PydanticObjectId) -> List[Profile]:
        """
        Get all profiles for a user.

        Args:
            user_id: User ID

        Returns:
            List[Profile]: List of profiles for this user
        """
        return await Profile.find({"user_id": user_id}).to_list()

    async def get_portfolios(self, user_id: PydanticObjectId) -> List[Portfolio]:
        """
        Get all portfolios for a user.

        Args:
            user_id: User ID

        Returns:
            List[Portfolio]: List of portfolios for this user
        """
        return await Portfolio.find({"user_id": user_id}).to_list()

    async def get_resumes(self, user_id: PydanticObjectId) -> List[Resume]:
        """
        Get all resumes for a user.

        Args:
            user_id: User ID

        Returns:
            List[Resume]: List of resumes for this user
        """
        return await Resume.find({"user_id": user_id}).to_list()

    async def update_last_login(self, user_id: PydanticObjectId) -> bool:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful, False otherwise
        """
        result = await User.find_one({"_id": user_id})
        if not result:
            return False

        result.last_login = datetime.now(timezone.utc)
        result.last_active = datetime.now(timezone.utc)
        await result.save()
        return True

    async def increment_login_attempts(self, email: EmailStr) -> int:
        """
        Increment login attempts for a user.

        Args:
            email: User email

        Returns:
            int: New login attempts count, or -1 if user not found
        """
        user = await self.get_by_email(email)
        if not user:
            return -1

        user.login_attempts += 1
        await user.save()
        return user.login_attempts

    async def reset_login_attempts(self, email: EmailStr) -> bool:
        """
        Reset login attempts for a user.

        Args:
            email: User email

        Returns:
            bool: True if successful, False otherwise
        """
        user = await self.get_by_email(email)
        if not user:
            return False

        current_time = datetime.now(timezone.utc)
        user.login_attempts = 0
        user.account_locked_until = current_time
        user.last_active = current_time

        await user.save()
        return True

    async def lock_account(self, email: EmailStr, lock_until: datetime) -> bool:
        """
        Lock a user account until a specified time.

        Args:
            email: User email
            lock_until: Time until which the account should be locked

        Returns:
            bool: True if successful, False otherwise
        """
        user = await self.get_by_email(email)
        if not user:
            return False

        # Ensure lock_until has timezone info
        if hasattr(lock_until, "tzinfo") and lock_until.tzinfo is None:
            lock_until = lock_until.replace(tzinfo=timezone.utc)

        user.account_locked_until = lock_until
        await user.save()
        return True


async def get_user_repository(self) -> UserRepository:
    """
    Get the user repository.
    """
    return UserRepository()
