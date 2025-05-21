"""Profile service for user profile management."""

from typing import Any, Dict, Optional

from beanie import PydanticObjectId

from config.logging_config import get_logger

from ..exceptions.base import NotFoundException
from ..models.profile import (
    PersonalInformation,
    Profile,
    PromptPreferences,
    SystemPreferences,
)
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

    async def get_profile_by_user_id(self, user_id: Any) -> Profile:
        """
        Get a user's profile.

        Args:
            user_id: User ID (PydanticObjectId or User object)

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

    async def get_profile_by_id(self, profile_id: PydanticObjectId) -> Profile:
        """
        Get a profile by its ID.

        Args:
            profile_id: Profile ID (PydanticObjectId)

        Returns:
            Profile: User profile

        Raises:
            NotFoundException: If profile not found
            ValueError: If profile_id is not a valid ObjectId
        """
        try:
            # Get profile by ID
            profile = await self.profile_repository.get_by_id(profile_id)

            if not profile:
                raise NotFoundException(f"Profile not found with ID: {profile_id}")

            return profile

        except NotFoundException:
            raise
        except ValueError as e:
            self.logger.error(f"Invalid profile ID format: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting profile by ID: {e}")
            raise NotFoundException(f"Could not retrieve profile: {str(e)}")

    async def create_profile(self, profile: Profile) -> Profile:
        """
        Create a new profile.

        Args:
            profile: Profile object to create

        Returns:
            Profile: Created profile

        Raises:
            NotFoundException: If user not found
            ValueError: If invalid data
        """
        try:
            # Check if user exists
            user_id = profile.user_id
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Check if profile already exists
            try:
                existing_profile = await self.get_profile_by_user_id(user_id)
                if existing_profile:
                    self.logger.warning(f"Profile already exists for user: {user_id}")
                    return existing_profile
            except NotFoundException:
                # This is expected if no profile exists yet
                pass

            # Ensure profile has personal_information
            if not profile.personal_information:
                self.logger.error("Profile must have personal_information")
                raise ValueError("Profile must have personal_information")

            # Create the profile
            created_profile = await self.profile_repository.create(profile)
            self.logger.info(f"Created new profile for user: {user_id}")
            return created_profile

        except NotFoundException:
            raise
        except ValueError as e:
            self.logger.error(f"Invalid data: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating profile: {e}")
            raise

    async def update_profile(self, profile: Profile) -> Profile:
        """
        Update a profile.

        Args:
            profile: Profile to update

        Returns:
            Profile: Updated profile

        Raises:
            NotFoundException: If profile not found
            ValueError: If profile data is invalid
            Exception: For other errors
        """
        self.logger.debug(f"Updating profile with ID: {profile.id}")

        try:
            # Check if profile exists
            existing_profile = await self.profile_repository.get_by_id(profile.id)
            if not existing_profile:
                raise NotFoundException(f"Profile not found with ID: {profile.id}")

            # Update the profile using our new method
            updated_profile = await self.profile_repository.update_by_object(profile)
            if not updated_profile:
                raise Exception(f"Failed to update profile with ID: {profile.id}")

            self.logger.info(f"Updated profile for user: {profile.user_id}")
            return updated_profile

        except NotFoundException:
            raise
        except ValueError as e:
            self.logger.error(f"Invalid profile data: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating profile: {e}")
            raise

    async def update_personal_information(
        self, profile_id: PydanticObjectId, personal_information: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update personal information fields for a profile.

        Args:
            profile_id: Profile ID
            personal_information: Dictionary with personal information fields to update

        Returns:
            Dict[str, Any]: Updated personal information

        Raises:
            NotFoundException: If profile not found
            ValueError: If personal info data is invalid
            Exception: For other errors
        """
        self.logger.debug(f"Updating personal information for profile: {profile_id}")

        try:
            # Check if profile exists
            existing_profile = await self.profile_repository.get_by_id(profile_id)
            if not existing_profile:
                raise NotFoundException(f"Profile not found with ID: {profile_id}")

            # Validate the personal information
            try:
                # If we're updating all fields, validate with the model
                if (
                    "full_name" in personal_information
                    and "email" in personal_information
                ):
                    PersonalInformation(**personal_information)
            except Exception as e:
                raise ValueError(f"Invalid personal information: {e}")

            # Update just the personal information
            updated_info = await self.profile_repository.update_personal_info(
                profile_id=profile_id, personal_information=personal_information
            )

            if not updated_info:
                raise Exception(
                    f"Failed to update personal information for profile: {profile_id}"
                )

            self.logger.info(f"Updated personal information for profile: {profile_id}")
            return updated_info

        except NotFoundException:
            raise
        except ValueError as e:
            self.logger.error(f"Invalid personal information data: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating personal information: {e}")
            raise

    async def get_personal_information(
        self, user_id: PydanticObjectId
    ) -> Dict[str, Any]:
        """
        Get personal information for a user.

        Args:
            user_id: User ID

        Returns:
            Dict[str, Any]: Personal information fields

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting personal information for user: {user_id}")

        try:
            # Get personal information from the repository
            personal_information = (
                await self.profile_repository.get_personal_information(user_id)
            )

            if not personal_information:
                # Check if profile exists but returned empty personal info
                profile = await self.profile_repository.get_by_user_id(user_id)
                if not profile:
                    raise NotFoundException(f"Profile not found for user: {user_id}")
                # Profile exists but has no personal info (unusual case)
                self.logger.warning(
                    f"Profile exists but has no personal information: {user_id}"
                )

            return personal_information

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting personal information: {e}")
            raise

    async def get_prompt_preferences(
        self, user_id: PydanticObjectId
    ) -> Optional[PromptPreferences]:
        """
        Get user prompt preferences.

        Args:
            user_id: User ID

        Returns:
            Optional[PromptPreferences]: Prompt preferences if found, None otherwise

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting prompt preferences for user: {user_id}")

        try:
            # Get preferences from the repository
            preferences = await self.profile_repository.get_prompt_preferences(user_id)

            if preferences is None:
                # Check if profile exists
                profile = await self.profile_repository.get_by_user_id(user_id)
                if not profile:
                    raise NotFoundException(f"Profile not found for user: {user_id}")

                # Profile exists but preferences are None
                self.logger.warning(
                    f"Profile exists but has no prompt preferences: {user_id}"
                )

            return preferences

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting prompt preferences: {e}")
            raise

    async def get_system_preferences(
        self, user_id: PydanticObjectId
    ) -> Optional[SystemPreferences]:
        """
        Get user system preferences.

        Args:
            user_id: User ID

        Returns:
            Optional[SystemPreferences]: System preferences if found, None otherwise

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting system preferences for user: {user_id}")

        try:
            # Get preferences from the repository
            preferences = await self.profile_repository.get_system_preferences(user_id)

            if preferences is None:
                # Check if profile exists
                profile = await self.profile_repository.get_by_user_id(user_id)
                if not profile:
                    raise NotFoundException(f"Profile not found for user: {user_id}")

                # Profile exists but preferences are None
                self.logger.warning(
                    f"Profile exists but has no system preferences: {user_id}"
                )

            return preferences

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting system preferences: {e}")
            raise

    async def update_prompt_preferences(
        self, user_id: PydanticObjectId, update_data: Dict[str, Any]
    ) -> Optional[PromptPreferences]:
        """
        Update prompt preferences for a user.

        Args:
            user_id: User ID
            update_data: Dictionary with prompt preference fields to update

        Returns:
            Updated PromptPreferences object or None if update failed

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Updating prompt preferences for user: {user_id}")
        try:
            # Ensure profile exists first
            profile = await self.profile_repository.get_by_user_id(user_id)
            if not profile:
                raise NotFoundException(f"Profile not found for user: {user_id}")

            # Delegate update to repository
            updated_prefs = await self.profile_repository.update_prompt_preferences(
                profile.id, update_data
            )
            if updated_prefs:
                self.logger.info(f"Prompt preferences updated for user: {user_id}")
            else:
                self.logger.warning(
                    f"Failed to update prompt preferences for user: {user_id}"
                )
                # Consider raising an exception if update failure is critical

            return updated_prefs
        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating prompt preferences: {e}")
            raise Exception(f"Failed to update prompt preferences: {str(e)}")

    async def update_system_preferences(
        self, user_id: PydanticObjectId, update_data: Dict[str, Any]
    ) -> Optional[SystemPreferences]:
        """
        Update system preferences for a user.

        Args:
            user_id: User ID
            update_data: Dictionary with system preference fields to update

        Returns:
            Updated SystemPreferences object or None if update failed

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Updating system preferences for user: {user_id}")
        try:
            # Ensure profile exists first
            profile = await self.profile_repository.get_by_user_id(user_id)
            if not profile:
                raise NotFoundException(f"Profile not found for user: {user_id}")

            # Delegate update to repository
            updated_prefs = await self.profile_repository.update_system_preferences(
                profile.id, update_data
            )
            if updated_prefs:
                self.logger.info(f"System preferences updated for user: {user_id}")
            else:
                self.logger.warning(
                    f"Failed to update system preferences for user: {user_id}"
                )
                # Consider raising an exception if update failure is critical

            return updated_prefs
        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating system preferences: {e}")
            raise Exception(f"Failed to update system preferences: {str(e)}")

    async def get_api_keys(self, user_id: PydanticObjectId) -> Dict[str, str]:
        """
        Get API keys for a user.

        Args:
            user_id: User ID

        Returns:
            Dict[str, str]: Dictionary of API keys

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting API keys for user: {user_id}")

        try:
            # Get API keys from the repository
            api_keys = await self.profile_repository.get_api_keys(user_id)

            if not api_keys and api_keys != {}:  # Check if None rather than empty dict
                # Check if profile exists
                profile = await self.profile_repository.get_by_user_id(user_id)
                if not profile:
                    raise NotFoundException(f"Profile not found for user: {user_id}")

                # Profile exists but has no API keys (return empty dict)
                self.logger.info(f"Profile exists but has no API keys: {user_id}")
                return {}

            return api_keys

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting API keys: {e}")
            raise

    async def get_signature_key(self, user_id: PydanticObjectId) -> Optional[str]:
        """
        Get the signature key for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[str]: Signature key if exists, None otherwise

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting signature key for user: {user_id}")

        try:
            # Get profile
            profile = await self.profile_repository.get_by_user_id(user_id)

            if not profile:
                raise NotFoundException(f"Profile not found for user: {user_id}")

            return profile.signature_key

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting signature key: {e}")
            raise

    async def get_signature_url(self, user_id: PydanticObjectId) -> Optional[str]:
        """
        Get the signature URL for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[str]: Signature URL if exists, None otherwise

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting signature URL for user: {user_id}")

        try:
            # Get profile
            profile = await self.profile_repository.get_by_user_id(user_id)

            if not profile:
                raise NotFoundException(f"Profile not found for user: {user_id}")

            if not profile.signature_key:
                return None

            # Get storage provider
            from core.services.storage_service import get_storage_provider

            storage_provider = get_storage_provider()

            # Get URL for the signature
            return storage_provider.get_url(profile.signature_key)

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting signature URL: {e}")
            raise

    async def get_profile_picture_url(self, user_id: PydanticObjectId) -> Optional[str]:
        """
        Get the profile picture URL for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[str]: Profile picture URL if exists, None otherwise

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting profile picture URL for user: {user_id}")

        try:
            # Get profile
            profile = await self.profile_repository.get_by_user_id(user_id)

            if not profile:
                raise NotFoundException(f"Profile not found for user: {user_id}")

            if not profile.profile_picture_key:
                return None

            # Get storage provider
            from core.services.storage_service import get_storage_provider

            storage_provider = get_storage_provider()

            # Get URL for the profile picture
            return storage_provider.get_url(profile.profile_picture_key)

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting profile picture URL: {e}")
            raise
