"""Profile service for user profile management."""

import logging
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId
from bson import ObjectId

from config.logging_config import get_logger

from ..exceptions.base import NotFoundException
from ..models.profile import Profile
from ..models.user import User
from ..repositories.profile_repository import ProfileRepository
from ..repositories.user_repository import UserRepository

logger = get_logger(__name__)


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
        self.logger = get_logger(self.__class__.__name__)

    async def get_profile(self, user_id: Any) -> Profile:
        """
        Get a user's profile.

        Args:
            user_id: User ID (ObjectId, PydanticObjectId, str, or User object)

        Returns:
            Profile: User profile

        Raises:
            NotFoundException: If profile not found
            ValueError: If user_id is not a valid ObjectId
        """
        try:
            # Try to get profile directly
            profile = await self.profile_repository.get_by_user_id(user_id)

            if profile:
                self.logger.debug(f"Found profile for user: {user_id}")
                return profile

            # If not found, check if user exists
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # User exists but no profile
            self.logger.warning(f"User exists but no profile found: {user_id}")
            raise NotFoundException(f"Profile not found for user: {user_id}")

        except NotFoundException:
            raise
        except ValueError as e:
            self.logger.error(f"Invalid user ID format: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting profile: {e}")
            raise NotFoundException(f"Could not retrieve profile: {str(e)}")

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
        try:
            # First check if user exists
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Check if profile already exists
            existing_profile = await self.profile_repository.get_by_user_id(user_id)
            if existing_profile:
                self.logger.warning(f"Profile already exists for user: {user_id}")
                return existing_profile

            # Create new profile
            profile = await self.profile_repository.create_for_user(
                user, full_name, email
            )
            if not profile:
                raise Exception("Failed to create profile")

            self.logger.info(f"Created new profile for user: {user_id}")
            return profile

        except NotFoundException:
            raise
        except ValueError as e:
            self.logger.error(f"Invalid user ID format: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating profile: {e}")
            raise

    async def update_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> Profile:
        """
        Update a user's profile.

        Args:
            user_id: User ID
            profile_data: Updated profile data

        Returns:
            Profile: Updated profile

        Raises:
            NotFoundException: If profile not found
            ValueError: If user_id is not a valid ObjectId
        """
        try:
            # Get existing profile
            profile = await self.get_profile(user_id)

            # Update personal info
            if "personal_info" in profile_data:
                success = await self.profile_repository.update_personal_info(
                    profile.id, profile_data["personal_info"]
                )
                if not success:
                    raise Exception("Failed to update personal info")

            # Update preferences
            if "preferences" in profile_data:
                success = await self.profile_repository.update_preferences(
                    profile.id, profile_data["preferences"]
                )
                if not success:
                    raise Exception("Failed to update preferences")

            # Get and return updated profile
            return await self.get_profile(user_id)

        except NotFoundException:
            raise
        except ValueError as e:
            self.logger.error(f"Invalid user ID format: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating profile: {e}")
            raise
