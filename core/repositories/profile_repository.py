"""Profile repository implementation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from beanie import PydanticObjectId
from bson import ObjectId

from config.logging_config import get_logger

from ..models.profile import PersonalInformation, Preferences, Profile
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
                profile.created_at = datetime.now(timezone.utc)
            if not profile.updated_at:
                profile.updated_at = datetime.now(timezone.utc)

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

    async def update(
        self,
        profile_id: Union[str, PydanticObjectId, ObjectId],
        updates: Dict[str, Any] = None,
        profile: Profile = None,
    ) -> Optional[Profile]:
        """Update an existing profile.

        Args:
            profile_id: ID of the profile to update
            updates: Dictionary of fields to update (optional)
            profile: Full Profile object with updates (optional)

        Returns:
            Optional[Profile]: Updated profile if successful, None otherwise

        Raises:
            ValueError: If neither updates nor profile is provided
            Exception: If update fails
        """
        try:
            # Convert ID to ObjectId
            object_id = self._ensure_object_id(profile_id)
            if not object_id:
                self.logger.error(f"Invalid profile ID: {profile_id}")
                return None

            # Handle different update methods
            if profile is not None:
                # Full profile object update
                if not profile.id:
                    profile.id = object_id
                profile.updated_at = datetime.now(timezone.utc)

                self.logger.debug(f"Updating profile with ID: {profile.id}")
                await profile.save()
                self.logger.info(f"Updated profile for user: {profile.user_id}")
                return profile

            elif updates is not None:
                # Partial update with specific fields
                result = await Profile.find_one({"_id": object_id})
                if not result:
                    self.logger.warning(f"Profile not found for update: {profile_id}")
                    return None

                # Update specified fields
                for key, value in updates.items():
                    if hasattr(result, key):
                        setattr(result, key, value)

                # Update timestamp
                result.updated_at = datetime.now(timezone.utc)

                # Save changes
                self.logger.debug(
                    f"Updating profile fields: {', '.join(updates.keys())}"
                )
                await result.save()
                self.logger.info(f"Updated profile fields for user: {result.user_id}")
                return result

            else:
                raise ValueError(
                    "Either profile object or updates dictionary must be provided"
                )

        except Exception as e:
            self.logger.error(f"Error updating profile: {e}")
            raise

    async def update_by_object(self, profile: Profile) -> Optional[Profile]:
        """Update a profile using a full Profile object.

        This is a convenience method that calls the main update method.

        Args:
            profile: Profile object with updates

        Returns:
            Optional[Profile]: Updated profile if successful, None otherwise
        """
        if not profile or not profile.id:
            self.logger.warning("Profile object missing or has no ID")
            return None

        return await self.update(profile_id=profile.id, profile=profile)

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
        self,
        profile_id: Union[str, PydanticObjectId, ObjectId],
        preferences: Preferences,
    ) -> Optional[Preferences]:
        """Update preferences for a profile.

        Args:
            profile_id: Profile ID
            preferences: Updated preferences object

        Returns:
            Optional[Preferences]: Updated preferences if successful, None otherwise
        """
        try:
            # Create an updates dictionary with the preferences
            updates = {"preferences": preferences}

            # Update the profile
            updated_profile = await self.update(profile_id=profile_id, updates=updates)

            if not updated_profile:
                return None

            return updated_profile.preferences
        except Exception as e:
            self.logger.error(f"Error updating preferences: {e}")
            return None

    async def update_personal_info(
        self,
        profile_id: Union[str, PydanticObjectId, ObjectId],
        personal_information: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update personal information for a profile.

        Args:
            profile_id: ID of the profile to update
            personal_information: Dictionary of personal information fields to update

        Returns:
            Dict[str, Any]: Updated personal information

        Raises:
            ValueError: If profile_id is invalid
            Exception: If update fails
        """
        try:
            # Convert ID to ObjectId
            object_id = self._ensure_object_id(profile_id)
            if not object_id:
                self.logger.error(f"Invalid profile ID: {profile_id}")
                return {}

            # Get the profile
            profile = await Profile.find_one({"_id": object_id})
            if not profile:
                self.logger.warning(f"Profile not found for update: {profile_id}")
                return {}

            # Update personal information fields
            for key, value in personal_information.items():
                if hasattr(profile.personal_information, key):
                    setattr(profile.personal_information, key, value)

            # Update timestamp
            profile.updated_at = datetime.now(timezone.utc)

            # Save changes
            self.logger.debug(
                f"Updating personal information fields: {', '.join(personal_information.keys())}"
            )
            await profile.save()
            self.logger.info(
                f"Updated personal information for user: {profile.user_id}"
            )

            # Return the updated personal information
            return profile.personal_information.model_dump()

        except Exception as e:
            self.logger.error(f"Error updating personal information: {e}")
            raise

    async def create_for_user(
        self, user: User, full_name: str, email: str
    ) -> Optional[Profile]:
        """Create a new profile for a user.

        Args:
            user: User object
            full_name: User's full name
            email: User's email address

        Returns:
            Optional[Profile]: Created profile if successful, None otherwise
        """
        try:
            if not user or not user.id:
                self.logger.warning("Invalid user object provided")
                return None

            # Check if profile already exists
            existing_profile = await self.get_by_user(user)
            if existing_profile:
                self.logger.info(f"Profile already exists for user: {user.id}")
                return existing_profile

            # Create personal information
            personal_information = PersonalInformation(
                full_name=full_name,
                email=email,
            )

            # Create profile with default preferences
            profile = Profile(
                user_id=user.id,
                personal_information=personal_information,
                preferences=Preferences(),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Save the profile
            self.logger.debug(f"Creating profile for user: {user.id}")
            await profile.create()
            self.logger.info(f"Created profile with ID: {profile.id}")
            return profile

        except Exception as e:
            self.logger.error(f"Error creating profile for user: {e}")
            return None

    # Enhanced methods for direct section access

    async def get_personal_information(
        self, user_id: PydanticObjectId
    ) -> Dict[str, Any]:
        """Get personal information for a user.

        Args:
            user_id: User ID

        Returns:
            Dict[str, Any]: Dictionary with personal information fields
        """
        try:
            profile = await self.get_by_user_id(user_id)
            if not profile:
                self.logger.warning(f"Profile not found for user: {user_id}")
                return {}

            # Return the personal information as a dictionary
            return profile.personal_information.model_dump()

        except Exception as e:
            self.logger.error(f"Error getting personal information: {e}")
            return {}

    async def get_preferences(self, user_id: PydanticObjectId) -> Optional[Preferences]:
        """
        Get user preferences.

        Args:
            user_id: User ID (string or ObjectId)

        Returns:
            Optional[Preferences]: User preferences if found, None otherwise
        """
        profile = await self.get_by_user_id(user_id)
        return profile.preferences if profile else None

    async def get_section_preferences(
        self, user_id: PydanticObjectId
    ) -> Dict[str, str]:
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

    async def get_api_keys(self, user_id: PydanticObjectId) -> Dict[str, str]:
        """
        Get API keys for a user.

        Args:
            user_id: User ID (string or ObjectId)

        Returns:
            Dict[str, str]: Dictionary of API keys
        """
        profile = await self.get_by_user_id(user_id)
        return profile.api_keys if profile and hasattr(profile, "api_keys") else {}


async def get_profile_repository() -> ProfileRepository:
    """
    Get the profile repository.
    """
    return ProfileRepository()
