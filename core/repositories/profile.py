"""Profile repository implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.profile import Preferences, Profile
from ..models.resume import Resume
from ..models.user import User
from .base import BeanieRepository


class ProfileRepository(BeanieRepository[Profile]):
    """Repository for Profile documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Profile)

    async def get_by_user(self, user: User) -> Optional[Profile]:
        """
        Get profile for a user.

        Args:
            user: User

        Returns:
            Optional[Profile]: Profile if found, None otherwise
        """
        return await Profile.find_one({"user_id": user.id})

    async def get_by_user_id(self, user_id: str) -> Optional[Profile]:
        """
        Get profile for a user by user ID.

        Args:
            user_id: User ID

        Returns:
            Optional[Profile]: Profile if found, None otherwise
        """
        return await Profile.find_one({"user_id": user_id})

    async def get_user(self, profile_id: str) -> Optional[User]:
        """
        Get the user associated with this profile.

        Args:
            profile_id: Profile ID

        Returns:
            Optional[User]: User if found, None otherwise
        """
        profile = await Profile.find_one({"_id": profile_id})
        if not profile:
            return None
        return await User.get(profile.user_id)

    async def get_resumes(self, profile_id: str) -> List[Resume]:
        """
        Get all resumes that use this profile.

        Args:
            profile_id: Profile ID

        Returns:
            List[Resume]: List of resumes using this profile
        """
        return await Resume.find({"profile_id": profile_id}).to_list()

    async def update_preferences(
        self, profile_id: str, preferences: Preferences
    ) -> bool:
        """
        Update preferences for a profile.

        Args:
            profile_id: Profile ID
            preferences: Updated preferences object

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Profile.find_one({"_id": profile_id})
        if not result:
            return False

        result.preferences = preferences
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_personal_info(
        self, profile_id: str, personal_info: Dict[str, Any]
    ) -> bool:
        """
        Update personal information for a profile.

        Args:
            profile_id: Profile ID
            personal_info: Updated personal information

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Profile.find_one({"_id": profile_id})
        if not result:
            return False

        # Update personal information fields
        for key, value in personal_info.items():
            if hasattr(result, key):
                setattr(result, key, value)

        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def create_for_user(self, user: User, full_name: str, email: str) -> Profile:
        """
        Create a new profile for a user.

        Args:
            user: User
            full_name: Full name
            email: Email address

        Returns:
            Profile: Created profile
        """
        profile = Profile(
            user_id=user.id,
            full_name=full_name,
            email=email,
            preferences=Preferences(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await profile.create()
        return profile
