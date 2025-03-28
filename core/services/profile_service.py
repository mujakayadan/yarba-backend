"""Profile service for user profile management."""

from typing import Any, Dict

from beanie import PydanticObjectId

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
        self, profile_id: PydanticObjectId, personal_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update personal information fields for a profile.

        Args:
            profile_id: Profile ID
            personal_info: Dictionary with personal information fields to update

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

            # Update just the personal information
            updated_info = await self.profile_repository.update_personal_info(
                profile_id=profile_id, personal_info=personal_info
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
            personal_info = await self.profile_repository.get_personal_information(
                user_id
            )

            if not personal_info:
                # Check if profile exists but returned empty personal info
                profile = await self.profile_repository.get_by_user_id(user_id)
                if not profile:
                    raise NotFoundException(f"Profile not found for user: {user_id}")
                # Profile exists but has no personal info (unusual case)
                self.logger.warning(
                    f"Profile exists but has no personal information: {user_id}"
                )

            return personal_info

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting personal information: {e}")
            raise

    async def get_preferences(self, user_id: PydanticObjectId) -> Any:
        """
        Get user preferences.

        Args:
            user_id: User ID

        Returns:
            Preferences object if found, None otherwise

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting preferences for user: {user_id}")

        try:
            # Get preferences from the repository
            preferences = await self.profile_repository.get_preferences(user_id)

            if preferences is None:
                # Check if profile exists
                profile = await self.profile_repository.get_by_user_id(user_id)
                if not profile:
                    raise NotFoundException(f"Profile not found for user: {user_id}")

                # Profile exists but preferences are None
                self.logger.warning(f"Profile exists but has no preferences: {user_id}")

            return preferences

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting preferences: {e}")
            raise

    async def get_section_preferences(
        self, user_id: PydanticObjectId
    ) -> Dict[str, str]:
        """
        Get section preferences for content generation.

        Args:
            user_id: User ID

        Returns:
            Dict[str, str]: Dictionary of section preferences

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Getting section preferences for user: {user_id}")

        try:
            # Get section preferences from the repository
            section_prefs = await self.profile_repository.get_section_preferences(
                user_id
            )

            if not section_prefs:
                # Check if profile exists but has no section preferences
                profile = await self.profile_repository.get_by_user_id(user_id)
                if not profile:
                    raise NotFoundException(f"Profile not found for user: {user_id}")

                # Profile exists but has no section preferences (return empty dict)
                self.logger.info(
                    f"Profile exists but has no section preferences: {user_id}"
                )

            return section_prefs

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error getting section preferences: {e}")
            raise

    async def update_preferences(
        self, profile_id: PydanticObjectId, preferences: Any
    ) -> Any:
        """
        Update user preferences.

        Args:
            profile_id: Profile ID
            preferences: Preferences object

        Returns:
            Updated preferences if successful

        Raises:
            NotFoundException: If profile not found
            Exception: For other errors
        """
        self.logger.debug(f"Updating preferences for profile: {profile_id}")

        try:
            # Check if profile exists
            existing_profile = await self.profile_repository.get_by_id(profile_id)
            if not existing_profile:
                raise NotFoundException(f"Profile not found with ID: {profile_id}")

            # Update the preferences
            updated_prefs = await self.profile_repository.update_preferences(
                profile_id=profile_id, preferences=preferences
            )

            if updated_prefs is None:
                raise Exception(
                    f"Failed to update preferences for profile: {profile_id}"
                )

            self.logger.info(f"Updated preferences for profile: {profile_id}")
            return updated_prefs

        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error updating preferences: {e}")
            raise

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
