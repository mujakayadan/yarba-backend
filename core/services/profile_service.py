"""Profile service for user profile management."""

from typing import Any, Union

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

    async def get_profile_by_id(
        self, profile_id: Union[str, PydanticObjectId, ObjectId]
    ) -> Profile:
        """
        Get a profile by its ID.

        Args:
            profile_id: Profile ID (ObjectId, PydanticObjectId, or str)

        Returns:
            Profile: User profile

        Raises:
            NotFoundException: If profile not found
            ValueError: If profile_id is not a valid ObjectId
        """
        try:
            # Convert to PydanticObjectId if string
            if isinstance(profile_id, str):
                if not ObjectId.is_valid(profile_id):
                    raise ValueError(f"Invalid ObjectId format: {profile_id}")
                profile_id = PydanticObjectId(profile_id)

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
                existing_profile = await self.get_profile(user_id)
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
        Update a user's profile.

        Args:
            profile: Profile object with updates

        Returns:
            Profile: Updated profile

        Raises:
            NotFoundException: If profile not found
            ValueError: If profile data is invalid
        """
        try:
            # Verify profile exists
            existing_profile = await self.profile_repository.get_by_id(profile.id)
            if not existing_profile:
                raise NotFoundException(f"Profile not found with ID: {profile.id}")

            # Update the profile
            updated_profile = await self.profile_repository.update(profile)
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
