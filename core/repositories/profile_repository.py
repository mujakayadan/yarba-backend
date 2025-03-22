"""Profile repository implementation."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from beanie import PydanticObjectId
from bson import ObjectId
from bson.errors import InvalidId

from config.logging_config import get_logger

from ..models.profile import Preferences, Profile
from ..models.resume import Resume
from ..models.user import User
from .base_repository import BeanieRepository


class ProfileRepository(BeanieRepository[Profile]):
    """Repository for Profile documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Profile)
        self.logger = get_logger(self.__class__.__name__)

    def _ensure_object_id(self, id_value: Any) -> Optional[ObjectId]:
        """Convert various ID types to ObjectId.

        Args:
            id_value: ID value to convert (str, ObjectId, PydanticObjectId, etc.)

        Returns:
            ObjectId or None if conversion fails
        """
        try:
            if isinstance(id_value, ObjectId):
                return id_value
            elif isinstance(id_value, PydanticObjectId):
                return ObjectId(str(id_value))
            elif isinstance(id_value, str):
                if ObjectId.is_valid(id_value):
                    return ObjectId(id_value)
                else:
                    self.logger.warning(f"Invalid ObjectId format: {id_value}")
                    return None
            elif hasattr(id_value, "id"):  # For User objects
                return self._ensure_object_id(id_value.id)
            else:
                # Try string conversion as last resort
                str_value = str(id_value)
                if ObjectId.is_valid(str_value):
                    return ObjectId(str_value)
                self.logger.warning(
                    f"Could not convert {type(id_value)} to ObjectId: {id_value}"
                )
                return None
        except Exception as e:
            self.logger.error(f"Error converting to ObjectId: {e}")
            return None

    async def create(self, profile: Profile) -> Profile:
        """Create a new profile.

        Args:
            profile: Profile object to create

        Returns:
            Profile: Created profile

        Raises:
            ValueError: If required fields are missing
            Exception: If creation fails
        """
        try:
            # Ensure timestamps are set
            if not profile.created_at:
                profile.created_at = datetime.utcnow()
            if not profile.updated_at:
                profile.updated_at = datetime.utcnow()

            # Ensure user_id is valid ObjectId
            if not profile.user_id or not self._ensure_object_id(profile.user_id):
                raise ValueError(f"Invalid user_id: {profile.user_id}")

            # Create the profile
            self.logger.debug(f"Creating profile for user: {profile.user_id}")
            await profile.create()
            self.logger.info(f"Created profile with ID: {profile.id}")
            return profile
        except Exception as e:
            self.logger.error(f"Error creating profile: {e}")
            raise

    async def update(self, profile: Profile) -> Profile:
        """Update an existing profile.

        Args:
            profile: Profile object with updates

        Returns:
            Profile: Updated profile

        Raises:
            ValueError: If profile ID is invalid
            Exception: If update fails
        """
        try:
            # Ensure profile has an ID
            if not profile.id:
                raise ValueError("Profile ID is required for updates")

            # Update timestamp
            profile.updated_at = datetime.utcnow()

            # Save the profile
            self.logger.debug(f"Updating profile with ID: {profile.id}")
            await profile.save()
            self.logger.info(f"Updated profile for user: {profile.user_id}")
            return profile
        except Exception as e:
            self.logger.error(f"Error updating profile: {e}")
            raise

    async def get_by_user(self, user: User) -> Optional[Profile]:
        """Get profile for a user.

        Args:
            user: User object

        Returns:
            Optional[Profile]: Profile if found, None otherwise
        """
        if not user or not user.id:
            self.logger.warning("Invalid user object provided")
            return None

        object_id = self._ensure_object_id(user.id)
        if not object_id:
            return None

        self.logger.debug(f"Getting profile for user: {object_id}")
        return await Profile.find_one({"user_id": object_id})

    async def get_by_user_id(self, user_id: Any) -> Optional[Profile]:
        """Get profile for a user by user ID.

        Args:
            user_id: User ID (ObjectId, PydanticObjectId, str, or User object)

        Returns:
            Optional[Profile]: Profile if found, None otherwise
        """
        object_id = self._ensure_object_id(user_id)
        if not object_id:
            return None

        self.logger.debug(f"Getting profile by user_id: {object_id}")
        return await Profile.find_one({"user_id": object_id})

    async def get_by_id(
        self, profile_id: Union[str, PydanticObjectId, ObjectId]
    ) -> Optional[Profile]:
        """Get profile by its ID.

        Args:
            profile_id: Profile ID (ObjectId, PydanticObjectId, or str)

        Returns:
            Optional[Profile]: Profile if found, None otherwise
        """
        object_id = self._ensure_object_id(profile_id)
        if not object_id:
            return None

        self.logger.debug(f"Getting profile by ID: {object_id}")
        return await Profile.find_one({"_id": object_id})

    async def get_user(self, profile_id: str) -> Optional[User]:
        """Get the user associated with this profile.

        Args:
            profile_id: Profile ID

        Returns:
            Optional[User]: User if found, None otherwise
        """
        object_id = self._ensure_object_id(profile_id)
        if not object_id:
            return None

        profile = await Profile.find_one({"_id": object_id})
        if not profile:
            return None

        return await User.get(profile.user_id)

    async def get_resumes(self, profile_id: str) -> List[Resume]:
        """Get all resumes that use this profile.

        Args:
            profile_id: Profile ID

        Returns:
            List[Resume]: List of resumes using this profile
        """
        object_id = self._ensure_object_id(profile_id)
        if not object_id:
            return []

        return await Resume.find({"profile_id": object_id}).to_list()

    async def update_preferences(
        self, profile_id: str, preferences: Preferences
    ) -> bool:
        """Update preferences for a profile.

        Args:
            profile_id: Profile ID
            preferences: Updated preferences object

        Returns:
            bool: True if successful, False otherwise
        """
        object_id = self._ensure_object_id(profile_id)
        if not object_id:
            return False

        result = await Profile.find_one({"_id": object_id})
        if not result:
            return False

        result.preferences = preferences
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_personal_info(
        self, profile_id: str, personal_info: Dict[str, Any]
    ) -> bool:
        """Update personal information for a profile.

        Args:
            profile_id: Profile ID
            personal_info: Updated personal information

        Returns:
            bool: True if successful, False otherwise
        """
        object_id = self._ensure_object_id(profile_id)
        if not object_id:
            return False

        result = await Profile.find_one({"_id": object_id})
        if not result:
            return False

        # Update personal information fields
        for key, value in personal_info.items():
            if hasattr(result, key):
                setattr(result, key, value)

        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def create_for_user(
        self, user: User, full_name: str, email: str
    ) -> Optional[Profile]:
        """Create a new profile for a user.

        Args:
            user: User
            full_name: Full name
            email: Email address

        Returns:
            Optional[Profile]: Created profile or None if creation fails
        """
        try:
            profile = Profile(
                user_id=user.id,
                full_name=full_name,
                email=email,
                phone="",
                address="",
                linkedin="",
                github="",
                website="",
                life_story="",
                preferences=Preferences(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            await profile.create()
            return profile
        except Exception as e:
            self.logger.error(f"Error creating profile: {e}")
            return None

    # Enhanced methods for direct section access

    async def get_personal_information(self, user_id: str) -> Optional[Profile]:
        """
        Get personal information for a user.

        Args:
            user_id: User ID (string or ObjectId)

        Returns:
            Optional[Profile]: Profile if found, None otherwise
        """
        return await self.get_by_user_id(user_id)

    async def get_preferences(self, user_id: str) -> Optional[Preferences]:
        """
        Get user preferences.

        Args:
            user_id: User ID (string or ObjectId)

        Returns:
            Optional[Preferences]: User preferences if found, None otherwise
        """
        profile = await self.get_by_user_id(user_id)
        return profile.preferences if profile else None

    async def get_section_preferences(self, user_id: str) -> Dict[str, str]:
        """
        Get section preferences.

        Args:
            user_id: User ID (string or ObjectId)

        Returns:
            Dict[str, str]: Dictionary of section preferences
        """
        profile = await self.get_by_user_id(user_id)

        if (
            not profile
            or not profile.preferences
            or not hasattr(profile.preferences, "section_preferences")
        ):
            return {}

        return profile.preferences.section_preferences

    async def get_api_keys(self, user_id: str) -> Dict[str, str]:
        """
        Get API keys for a user.

        Args:
            user_id: User ID (string or ObjectId)

        Returns:
            Dict[str, str]: Dictionary of API keys
        """
        profile = await self.get_by_user_id(user_id)
        return profile.api_keys if profile and hasattr(profile, "api_keys") else {}


async def get_profile_repository(self) -> ProfileRepository:
    """
    Get the profile repository.
    """
    return ProfileRepository()
