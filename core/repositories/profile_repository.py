"""Profile repository implementation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from beanie import PydanticObjectId
from bson import ObjectId

from config.logging_config import get_logger
from config.settings import settings

from ..models.profile import (
    PersonalInformation,
    Profile,
    PromptPreferences,
    SystemPreferences,
)
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

    async def exists(self, profile_id: Union[str, PydanticObjectId, ObjectId]) -> bool:
        """Check if a profile with the given ID exists.

        Args:
            profile_id: Profile ID (ObjectId, PydanticObjectId, or str)

        Returns:
            bool: True if profile exists, False otherwise
        """
        object_id = self._ensure_object_id(profile_id)
        if not object_id:
            return False

        self.logger.debug(f"Checking if profile exists with ID: {object_id}")
        profile = await Profile.find_one({"_id": object_id})
        return profile is not None

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

    async def update_prompt_preferences(
        self,
        profile_id: Union[str, PydanticObjectId, ObjectId],
        preferences: Dict[str, Any],
    ) -> Optional[PromptPreferences]:
        """Update prompt preferences for a profile.

        Args:
            profile_id: Profile ID
            preferences: Updated preferences dictionary

        Returns:
            Optional[PromptPreferences]: Updated preferences if successful, None otherwise
        """
        try:
            # Get the profile
            profile = await self.get_by_id(profile_id)
            if not profile:
                self.logger.warning(f"Profile not found: {profile_id}")
                return None

            # Update individual fields
            for section_name, section_prefs in preferences.items():
                if hasattr(profile.prompt_preferences, section_name):
                    # Get the current section dictionary
                    section_dict = getattr(profile.prompt_preferences, section_name, {})

                    # Add or update fields
                    if isinstance(section_dict, dict) and isinstance(
                        section_prefs, dict
                    ):
                        section_dict.update(section_prefs)
                        setattr(profile.prompt_preferences, section_name, section_dict)
                    else:
                        # Direct assignment if not a dict
                        setattr(profile.prompt_preferences, section_name, section_prefs)
                else:
                    self.logger.warning(
                        f"Unknown prompt preference section: {section_name}"
                    )

            # Update the profile
            profile.updated_at = datetime.now(timezone.utc)
            await profile.save()
            self.logger.info(f"Updated prompt preferences for profile: {profile_id}")

            return profile.prompt_preferences
        except Exception as e:
            self.logger.error(f"Error updating prompt preferences: {e}")
            return None

    async def update_system_preferences(
        self,
        profile_id: Union[str, PydanticObjectId, ObjectId],
        preferences: Dict[str, Any],
    ) -> Optional[SystemPreferences]:
        """Update system preferences for a profile.

        Args:
            profile_id: Profile ID
            preferences: Updated preferences dictionary

        Returns:
            Optional[SystemPreferences]: Updated preferences if successful, None otherwise
        """
        try:
            # Get the profile
            profile = await self.get_by_id(profile_id)
            if not profile:
                self.logger.warning(f"Profile not found: {profile_id}")
                return None

            # Update individual fields
            for section_name, section_prefs in preferences.items():
                if hasattr(profile.system_preferences, section_name):
                    # Get the current section dictionary
                    section_dict = getattr(profile.system_preferences, section_name, {})

                    # Add or update fields
                    if isinstance(section_dict, dict) and isinstance(
                        section_prefs, dict
                    ):
                        section_dict.update(section_prefs)
                        setattr(profile.system_preferences, section_name, section_dict)
                    else:
                        # Direct assignment if not a dict
                        setattr(profile.system_preferences, section_name, section_prefs)
                else:
                    self.logger.warning(
                        f"Unknown system preference section: {section_name}"
                    )

            # Update the profile
            profile.updated_at = datetime.now(timezone.utc)
            await profile.save()
            self.logger.info(f"Updated system preferences for profile: {profile_id}")

            return profile.system_preferences
        except Exception as e:
            self.logger.error(f"Error updating system preferences: {e}")
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

            # Create prompt preferences
            prompt_preferences = PromptPreferences()

            # Setup default project preferences
            prompt_preferences.project = {
                "max_projects": settings.preferences.project_max_projects,
                "bullet_points_per_project": settings.preferences.project_bullet_points_per_project,
            }

            # Setup default work experience preferences
            prompt_preferences.work_experience = {
                "max_jobs": settings.preferences.work_experience_max_jobs,
                "bullet_points_per_job": settings.preferences.work_experience_bullet_points_per_job,
            }

            # Setup default skills preferences
            prompt_preferences.skills = {
                "max_categories": settings.preferences.skills_max_categories,
                "min_per_category": settings.preferences.skills_min_per_category,
                "max_per_category": settings.preferences.skills_max_per_category,
            }

            # Setup default career summary preferences
            prompt_preferences.career_summary = {
                "min_words": settings.preferences.career_summary_min_words,
                "max_words": settings.preferences.career_summary_max_words,
            }

            # Setup default education preferences
            prompt_preferences.education = {
                "max_entries": settings.preferences.education_max_entries,
                "max_courses": settings.preferences.education_max_courses,
            }

            # Setup default awards preferences
            prompt_preferences.awards = {
                "max_awards": settings.preferences.awards_max_awards
            }

            # Setup default publications preferences
            prompt_preferences.publications = {
                "max_publications": settings.preferences.publications_max_publications
            }

            # Setup default cover letter preferences
            prompt_preferences.cover_letter = {
                "paragraphs": settings.preferences.cover_letter_paragraphs,
                "target_age": settings.preferences.cover_letter_target_age,
            }

            # Create system preferences
            system_preferences = SystemPreferences()

            # Override default templates
            system_preferences.templates = dict(
                settings.preferences.default_latex_templates
            )

            # Create profile with the new preference structures
            profile = Profile(
                user_id=user.id,
                personal_information=personal_information,
                prompt_preferences=prompt_preferences,
                system_preferences=system_preferences,
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

    async def get_prompt_preferences(
        self, user_id: PydanticObjectId
    ) -> Optional[PromptPreferences]:
        """
        Get user prompt preferences.

        Args:
            user_id: User ID

        Returns:
            Optional[PromptPreferences]: User prompt preferences if found, None otherwise
        """
        profile = await self.get_by_user_id(user_id)
        return profile.prompt_preferences if profile else None

    async def get_system_preferences(
        self, user_id: PydanticObjectId
    ) -> Optional[SystemPreferences]:
        """
        Get user system preferences.

        Args:
            user_id: User ID

        Returns:
            Optional[SystemPreferences]: User system preferences if found, None otherwise
        """
        profile = await self.get_by_user_id(user_id)
        return profile.system_preferences if profile else None

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

    async def update_llm_usage(
        self,
        user_id: Union[str, PydanticObjectId],
        tokens_used: int,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        model_name: str,
        operation_type: str,
    ) -> bool:
        """
        Update LLM usage statistics for a user.

        Args:
            user_id: User ID
            tokens_used: Total number of tokens used in this operation
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of this LLM operation in USD
            model_name: Name of the LLM model used
            operation_type: Type of operation (e.g., "generation", "extract_job_details")

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Validate user_id format
            object_id = self._ensure_object_id(user_id)
            if not object_id:
                self.logger.error(f"Invalid user_id format: {user_id}")
                return False

            # Get current profile
            profile = await self.get_by_user_id(user_id)
            if not profile:
                self.logger.error(f"Profile not found for user_id: {user_id}")
                return False

            # Get current date
            now = datetime.now(timezone.utc)
            month_key = now.strftime("%Y-%m")

            # Initialize if this is first usage
            if not profile.llm_usage.last_used:
                profile.llm_usage.last_used = now

            # Update total usage
            profile.llm_usage.total_tokens += tokens_used
            profile.llm_usage.total_input_tokens += input_tokens
            profile.llm_usage.total_output_tokens += output_tokens
            profile.llm_usage.total_cost += cost
            profile.llm_usage.last_used = now

            # Update current month usage
            profile.llm_usage.current_month_tokens += tokens_used
            profile.llm_usage.current_month_cost += cost

            # Add to monthly history
            if month_key not in profile.llm_usage.monthly_history:
                profile.llm_usage.monthly_history[month_key] = {
                    "tokens": 0,
                    "cost": 0.0,
                }
            profile.llm_usage.monthly_history[month_key]["tokens"] += tokens_used
            profile.llm_usage.monthly_history[month_key]["cost"] += cost

            # Update usage by model
            if model_name not in profile.llm_usage.usage_by_model:
                profile.llm_usage.usage_by_model[model_name] = {
                    "tokens": 0,
                    "cost": 0.0,
                }
            profile.llm_usage.usage_by_model[model_name]["tokens"] += tokens_used
            profile.llm_usage.usage_by_model[model_name]["cost"] += cost

            # Update usage by operation
            if operation_type not in profile.llm_usage.usage_by_operation:
                profile.llm_usage.usage_by_operation[operation_type] = {
                    "tokens": 0,
                    "cost": 0.0,
                }
            profile.llm_usage.usage_by_operation[operation_type][
                "tokens"
            ] += tokens_used
            profile.llm_usage.usage_by_operation[operation_type]["cost"] += cost

            # Save changes
            await profile.save()
            self.logger.info(
                f"Updated LLM usage for user_id: {user_id}, added {tokens_used} tokens, ${cost:.6f}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error updating LLM usage: {e}")
            return False

    async def get_llm_usage(
        self, user_id: Union[str, PydanticObjectId]
    ) -> Optional[Dict[str, Any]]:
        """
        Get LLM usage statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with LLM usage statistics or None if error
        """
        try:
            # Validate user_id format
            object_id = self._ensure_object_id(user_id)
            if not object_id:
                self.logger.error(f"Invalid user_id format: {user_id}")
                return None

            # Get current profile
            profile = await self.get_by_user_id(user_id)
            if not profile:
                self.logger.error(f"Profile not found for user_id: {user_id}")
                return None

            # Return usage data
            return profile.llm_usage.model_dump()

        except Exception as e:
            self.logger.error(f"Error retrieving LLM usage: {e}")
            return None

    async def check_llm_usage_limits(
        self, user_id: Union[str, PydanticObjectId]
    ) -> Dict[str, Any]:
        """
        Check if a user has exceeded their LLM usage limits.

        Args:
            user_id: User ID

        Returns:
            Dict with limit information: {
                "can_use": bool,
                "monthly_quota_exceeded": bool,
                "monthly_cost_exceeded": bool,
                "current_month_tokens": int,
                "current_month_cost": float,
                "monthly_quota": int or None,
                "monthly_cost_limit": float or None
            }
        """
        try:
            # Validate user_id format
            object_id = self._ensure_object_id(user_id)
            if not object_id:
                self.logger.error(f"Invalid user_id format: {user_id}")
                return {"can_use": False, "error": "Invalid user ID"}

            # Get current profile
            profile = await self.get_by_user_id(user_id)
            if not profile:
                self.logger.error(f"Profile not found for user_id: {user_id}")
                return {"can_use": False, "error": "Profile not found"}

            # Check for quota limits
            current_month_tokens = profile.llm_usage.current_month_tokens
            current_month_cost = profile.llm_usage.current_month_cost
            monthly_quota = profile.llm_usage.monthly_quota
            monthly_cost_limit = profile.llm_usage.monthly_cost_limit

            quota_exceeded = (
                monthly_quota is not None and current_month_tokens >= monthly_quota
            )
            cost_exceeded = (
                monthly_cost_limit is not None
                and current_month_cost >= monthly_cost_limit
            )

            # This month could be different from when token count started, do a check
            now = datetime.now(timezone.utc)
            current_month_key = now.strftime("%Y-%m")
            last_used = profile.llm_usage.last_used

            # If it's a new month, reset current month counters
            if last_used and last_used.strftime("%Y-%m") != current_month_key:
                await self.reset_current_month_usage(user_id)
                quota_exceeded = False
                cost_exceeded = False
                current_month_tokens = 0
                current_month_cost = 0.0

            return {
                "can_use": not (quota_exceeded or cost_exceeded),
                "monthly_quota_exceeded": quota_exceeded,
                "monthly_cost_exceeded": cost_exceeded,
                "current_month_tokens": current_month_tokens,
                "current_month_cost": current_month_cost,
                "monthly_quota": monthly_quota,
                "monthly_cost_limit": monthly_cost_limit,
            }

        except Exception as e:
            self.logger.error(f"Error checking LLM usage limits: {e}")
            return {"can_use": False, "error": str(e)}

    async def reset_current_month_usage(
        self, user_id: Union[str, PydanticObjectId]
    ) -> bool:
        """
        Reset the current month's usage counters.

        Args:
            user_id: User ID

        Returns:
            bool: True if reset was successful, False otherwise
        """
        try:
            # Validate user_id format
            object_id = self._ensure_object_id(user_id)
            if not object_id:
                self.logger.error(f"Invalid user_id format: {user_id}")
                return False

            # Get current profile
            profile = await self.get_by_user_id(user_id)
            if not profile:
                self.logger.error(f"Profile not found for user_id: {user_id}")
                return False

            # Reset current month counters
            profile.llm_usage.current_month_tokens = 0
            profile.llm_usage.current_month_cost = 0.0

            # Save changes
            await profile.save()
            self.logger.info(f"Reset current month LLM usage for user_id: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error resetting current month LLM usage: {e}")
            return False

    async def set_llm_usage_limits(
        self,
        user_id: Union[str, PydanticObjectId],
        monthly_quota: Optional[int] = None,
        monthly_cost_limit: Optional[float] = None,
    ) -> bool:
        """
        Set usage limits for a user.

        Args:
            user_id: User ID
            monthly_quota: Maximum number of tokens per month (None for unlimited)
            monthly_cost_limit: Maximum cost per month in USD (None for unlimited)

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Validate user_id format
            object_id = self._ensure_object_id(user_id)
            if not object_id:
                self.logger.error(f"Invalid user_id format: {user_id}")
                return False

            # Get current profile
            profile = await self.get_by_user_id(user_id)
            if not profile:
                self.logger.error(f"Profile not found for user_id: {user_id}")
                return False

            # Update limits
            profile.llm_usage.monthly_quota = monthly_quota
            profile.llm_usage.monthly_cost_limit = monthly_cost_limit

            # Save changes
            await profile.save()
            self.logger.info(
                f"Set LLM usage limits for user_id: {user_id}, "
                f"monthly_quota: {monthly_quota}, monthly_cost_limit: {monthly_cost_limit}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error setting LLM usage limits: {e}")
            return False


async def get_profile_repository() -> ProfileRepository:
    """
    Get the profile repository.
    """
    return ProfileRepository()
