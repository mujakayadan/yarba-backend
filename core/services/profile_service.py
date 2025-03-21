"""Profile service for user profile management."""

import logging
from typing import Dict, List, Optional

from ..exceptions.base import NotFoundException
from ..models.profile import Profile
from ..models.user import User
from ..repositories.profile_repository import ProfileRepository
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for user profile operations."""

    def __init__(
        self,
        profile_repository: ProfileRepository,
        user_repository: UserRepository,
    ):
        """
        Initialize the service.

        Args:
            profile_repository: Profile repository instance
            user_repository: User repository instance
        """
        self.profile_repository = profile_repository
        self.user_repository = user_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_profile(self, user_id: str) -> Profile:
        """
        Get a user's profile.

        Args:
            user_id: User ID

        Returns:
            Profile: User profile

        Raises:
            NotFoundException: If profile not found
        """
        profile = await self.profile_repository.get_by_user_id(user_id)

        if not profile:
            self.logger.warning(f"Profile not found for user: {user_id}")
            raise NotFoundException("Profile not found")

        return profile

    async def create_profile(self, user_id: str, full_name: str, email: str) -> Profile:
        """
        Create a new profile for a user.

        Args:
            user_id: User ID
            full_name: User's full name
            email: User's email

        Returns:
            Profile: Created profile

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        # Check if profile already exists
        existing_profile = await self.profile_repository.get_by_user_id(user_id)
        if existing_profile:
            self.logger.info(f"Profile already exists for user: {user_id}")
            return existing_profile

        profile = await self.profile_repository.create_for_user(user, full_name, email)
        self.logger.info(f"Profile created for user: {user_id}")

        return profile

    async def update_profile(self, user_id: str, update_data: Dict) -> Profile:
        """
        Update a user's profile.

        Args:
            user_id: User ID
            update_data: Profile data to update

        Returns:
            Profile: Updated profile

        Raises:
            NotFoundException: If profile not found
        """
        profile = await self.get_profile(user_id)

        # Update profile fields
        for key, value in update_data.items():
            if hasattr(profile, key) and key != "id" and key != "user":
                setattr(profile, key, value)

        updated_profile = await self.profile_repository.update(profile.id, profile)
        if not updated_profile:
            self.logger.error(f"Failed to update profile for user: {user_id}")
            raise NotFoundException("Profile not found")

        self.logger.info(f"Profile updated for user: {user_id}")
        return updated_profile
