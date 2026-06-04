"""Profile router for the API."""

from typing import Annotated

from beanie import PydanticObjectId
from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from pydantic import BaseModel, Field, field_validator

from api.dependencies.auth import CurrentActiveUser
from api.dependencies.services import get_profile_service
from api.schemas.profile import (
    LifeStoryPatch,
    LLMUsageResponse,
    LLMUsageSummary,
    PersonalInfoUpdate,
    ProfileCreate,
    ProfilePatch,
    ProfileUpdate,
    PromptPreferencesUpdate,
    SignatureResponse,
    SystemPreferencesUpdate,
)
from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.profile import (
    PersonalInformation,
    Profile,
    PromptPreferences,
    SystemPreferences,
)
from core.services.profile_service import ProfileService
from core.utils.object_id import require_object_id
from utils.storage import get_storage_provider

router = APIRouter()
logger = get_logger(__name__)


class ObjectIdPath(BaseModel):
    """Path parameter for ObjectId validation."""

    id: str = Field(..., description="ObjectId string")

    @classmethod
    @field_validator("id")
    def validate_object_id(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId format")
        return v


@router.get("/me", response_model=Profile)
async def get_my_profile(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get the current user's profile.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Profile
    """
    try:
        # Try to get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)
        return profile
    except NotFoundException:
        # Profile doesn't exist - create one automatically
        logger.info(
            f"Profile not found for user {current_user.id}, creating automatically"
        )
        from core.repositories.profile_repository import ProfileRepository

        profile_repo = ProfileRepository()

        # Create profile with defaults from application settings
        new_profile = await profile_repo.create_for_user(
            user=current_user,
            email=current_user.email,
            full_name=None,
        )

        if not new_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to auto-create profile",
            )

        return new_profile


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Create a new profile.

    Args:
        profile_data: Profile data
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Created profile
    """
    try:
        # Check if user already has a profile
        try:
            existing_profile = await profile_service.get_profile_by_user_id(
                current_user.id
            )
            if existing_profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already has a profile",
                )
        except NotFoundException:
            # This is expected if user doesn't have a profile yet
            pass

        # Create preferences if provided
        prompt_prefs = PromptPreferences()
        system_prefs = SystemPreferences()

        if profile_data.preferences:
            if "prompt" in profile_data.preferences:
                prompt_prefs = PromptPreferences(**profile_data.preferences["prompt"])
            if "system" in profile_data.preferences:
                system_prefs = SystemPreferences(**profile_data.preferences["system"])

        # Create personal information
        personal_information = PersonalInformation(
            **profile_data.personal_information.model_dump()
        )

        # Create profile
        profile = Profile(
            user_id=current_user.id,
            personal_information=personal_information,
            prompt_preferences=prompt_prefs,
            system_preferences=system_prefs,
        )

        # Save through service
        created_profile = await profile_service.create_profile(profile)
        return created_profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create profile: {str(e)}",
        )


@router.put("/me", response_model=Profile)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Update the current user's profile.

    Args:
        profile_data: Profile data
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Updated profile
    """
    try:
        # Get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Update personal information if provided
        if profile_data.personal_information:
            personal_info_data = profile_data.personal_information.model_dump(
                exclude_unset=True
            )

            if personal_info_data:
                # Update through service
                await profile_service.update_personal_information(
                    profile_id=require_object_id(profile.id),
                    personal_information=personal_info_data,
                )
                # Refresh profile
                profile = await profile_service.get_profile_by_id(
                    require_object_id(profile.id)
                )

        return profile
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}",
        )


@router.patch("/me", response_model=Profile)
async def patch_my_profile(
    profile_data: ProfilePatch,
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Patch specific fields of the current user's profile.

    Args:
        profile_data: Fields to update
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Updated profile
    """
    try:
        # Log the request body for debugging
        logger.debug(f"Patching profile for user: {current_user.id}")
        logger.debug(f"Patch data: {profile_data.model_dump(exclude_unset=True)}")

        # Get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)
        logger.debug(f"Found profile with ID: {profile.id}")

        # Update fields with provided values
        update_data = profile_data.model_dump(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                logger.debug(f"Setting field '{field}' to value: {value}")
                setattr(profile, field, value)

            try:
                # Update the profile
                logger.debug(f"Calling update_profile for profile ID: {profile.id}")
                updated_profile = await profile_service.update_profile(profile)
                logger.debug(f"Profile updated successfully: {updated_profile.id}")
                return updated_profile
            except Exception as inner_e:
                logger.error(f"Error updating profile: {inner_e}", exc_info=True)
                raise inner_e

        return profile
    except NotFoundException:
        logger.warning(f"Profile not found for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        # Add more details to the error for debugging
        logger.error(f"Failed to patch profile: {e}", exc_info=True)
        error_msg = f"Failed to patch profile: {str(e)}, type: {type(e).__name__}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )


@router.patch("/me/personal-information", response_model=Profile)
async def patch_my_personal_info(
    personal_info_data: PersonalInfoUpdate,
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Patch specific personal information fields of the current user's profile.

    Args:
        personal_info_data: Personal information fields to update
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Updated profile
    """
    try:
        # Get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Update personal information
        personal_info_update = personal_info_data.model_dump(exclude_unset=True)
        if personal_info_update:
            # Update through service
            await profile_service.update_personal_information(
                profile_id=require_object_id(profile.id),
                personal_information=personal_info_update,
            )

            # Refresh profile
            profile = await profile_service.get_profile_by_id(
                require_object_id(profile.id)
            )

        return profile
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to patch personal information: {str(e)}",
        )


@router.get("/me/personal-information", response_model=PersonalInformation)
async def get_my_personal_info(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get the personal information of the current user's profile.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Personal information
    """
    try:
        # Get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Return personal information
        if profile.personal_information:
            return profile.personal_information
        else:
            # Handle case where personal_information might be None
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personal information not found for this profile.",
            )

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Failed to get personal information: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get personal information: {str(e)}",
        )


@router.get("/{profile_id}", response_model=Profile)
async def get_profile(
    profile_id: Annotated[str, Path(..., description="Profile ID")],
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get a profile by ID.

    Args:
        profile_id: Profile ID
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Profile
    """
    # Validate ObjectId
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid profile ID format",
        )

    try:
        # Get profile by ID
        profile_obj_id = PydanticObjectId(profile_id)
        profile = await profile_service.get_profile_by_id(profile_obj_id)

        # Check if the profile belongs to the current user
        if profile.user_id != current_user.id:
            # Check if the profile is public
            if (
                not profile.preferences
                or not profile.preferences.privacy_preferences
                or not profile.preferences.privacy_preferences.get("profile_visibility")
                == "public"
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access this profile",
                )

        return profile
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve profile: {str(e)}",
        )


@router.patch("/me/life-story", response_model=Profile)
async def patch_my_life_story(
    life_story_data: LifeStoryPatch,
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Update only the life story field of the current user's profile.

    Args:
        life_story_data: Life story data
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Updated profile
    """
    try:
        # Log the request for debugging
        logger.debug(f"Updating life story for user: {current_user.id}")

        # Get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)
        logger.debug(f"Found profile with ID: {profile.id}")

        # Update life story
        profile.life_story = life_story_data.life_story
        logger.debug("Set life_story field, preparing to save")

        # Save through service
        try:
            updated_profile = await profile_service.update_profile(profile)
            logger.debug("Profile updated successfully with new life story")
            return updated_profile
        except Exception as inner_e:
            logger.error(
                f"Error updating profile with life story: {inner_e}", exc_info=True
            )
            raise inner_e
    except NotFoundException:
        logger.warning(f"Profile not found for user: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Failed to update life story: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update life story: {str(e)}",
        )


# Return just the life story string
class LifeStoryResponse(BaseModel):
    """Response model for returning just the life story."""

    life_story: str | None = None


@router.get("/me/life-story", response_model=LifeStoryResponse)
async def get_my_life_story(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get only the life story field of the current user's profile.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Life story content
    """
    try:
        # Get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Return just the life story
        return LifeStoryResponse(life_story=profile.life_story)
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Failed to get life story: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get life story: {str(e)}",
        )


class ProfilePictureResponse(BaseModel):
    """Response model for profile picture storage key."""

    profile_picture_key: str | None = None


@router.post("/me/profile-picture", response_model=ProfilePictureResponse)
async def upload_profile_picture(
    current_user: CurrentActiveUser,
    file: UploadFile = File(...),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Upload a profile picture image.

    Args:
        file: Profile picture image file
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Profile picture storage key
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Get storage provider
        storage_provider = get_storage_provider()

        # If user already has a profile picture, delete it
        if profile.profile_picture_key:
            await storage_provider.delete_file(profile.profile_picture_key)

        # Save the new profile picture (pass the UploadFile object directly)
        filename = await storage_provider.save_profile_picture(
            file, str(current_user.id)
        )

        # Update profile with the new profile picture
        profile.profile_picture_key = filename
        await profile_service.update_profile(profile)

        # Return the storage key
        return {"profile_picture_key": filename}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error uploading profile picture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile picture: {str(e)}",
        )


@router.delete("/me/profile-picture", response_model=ProfilePictureResponse)
async def delete_my_profile_picture(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Delete the current user's profile picture.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Empty profile picture key
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Get storage provider
        storage_provider = get_storage_provider()

        # If user has a profile picture, delete it
        if profile.profile_picture_key:
            success = await storage_provider.delete_file(profile.profile_picture_key)
            if not success:
                logger.warning(
                    f"Failed to delete profile picture file: {profile.profile_picture_key}"
                )

            # Update profile to remove profile picture reference
            profile.profile_picture_key = None
            await profile_service.update_profile(profile)

        return {"profile_picture_key": None}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error deleting profile picture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete profile picture: {str(e)}",
        )


@router.get("/me/profile-picture", response_model=ProfilePictureResponse)
async def get_my_profile_picture(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get the current user's profile picture key.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Profile picture storage key
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        return {"profile_picture_key": profile.profile_picture_key}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error getting profile picture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile picture: {str(e)}",
        )


@router.post("/me/signature", response_model=SignatureResponse)
async def upload_signature(
    current_user: CurrentActiveUser,
    file: UploadFile = File(...),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Upload a signature image.

    Args:
        file: Signature image file
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Signature storage key and URL
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Get storage provider
        storage_provider = get_storage_provider()

        # If user already has a signature, delete it
        if profile.signature_key:
            await storage_provider.delete_file(profile.signature_key)

        # Read the file content
        content = await file.read()

        # Save the new signature
        signature_key = await storage_provider.save_signature(
            content, str(current_user.id)
        )

        # Update profile with the new signature key
        profile.signature_key = signature_key
        await profile_service.update_profile(profile)

        # Get URL for the signature
        signature_url = storage_provider.get_url(signature_key)

        # Return the storage key and URL
        return {"signature_key": signature_key, "signature_url": signature_url}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error uploading signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload signature: {str(e)}",
        )


@router.delete("/me/signature", response_model=SignatureResponse)
async def delete_my_signature(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Delete the current user's signature.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Empty signature key and URL
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Get storage provider
        storage_provider = get_storage_provider()

        # If user has a signature, delete it
        if profile.signature_key:
            success = await storage_provider.delete_file(profile.signature_key)
            if not success:
                logger.warning(
                    f"Failed to delete signature file: {profile.signature_key}"
                )

            # Update profile to remove signature reference
            profile.signature_key = None
            await profile_service.update_profile(profile)

        return {"signature_key": None, "signature_url": None}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error deleting signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete signature: {str(e)}",
        )


@router.get("/me/signature", response_model=SignatureResponse)
async def get_my_signature(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get the current user's signature key and URL.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Signature storage key and URL
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Get signature URL using the new method
        signature_url = await profile_service.get_signature_url(current_user.id)

        return {"signature_key": profile.signature_key, "signature_url": signature_url}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error getting signature: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get signature: {str(e)}",
        )


@router.get("/me/llm-usage", response_model=LLMUsageResponse)
async def get_my_llm_usage(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get the current user's LLM usage statistics.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        LLM usage statistics
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Return LLM usage data
        return profile.llm_usage.model_dump()

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error getting LLM usage statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLM usage statistics: {str(e)}",
        )


@router.get("/me/llm-usage/summary", response_model=LLMUsageSummary)
async def get_my_llm_usage_summary(
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
):
    """Get a simplified summary of the current user's LLM usage statistics.

    This endpoint provides a dashboard-friendly overview of LLM usage without detailed breakdowns.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Simplified LLM usage summary
    """
    try:
        # Get current profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Calculate usage limit percentage
        usage_limit_percentage = 0.0
        if profile.llm_usage.monthly_quota and profile.llm_usage.monthly_quota > 0:
            usage_limit_percentage = min(
                100.0,
                (
                    profile.llm_usage.current_month_tokens
                    / profile.llm_usage.monthly_quota
                )
                * 100,
            )

        # Calculate cost limit percentage
        cost_limit_percentage = 0.0
        if (
            profile.llm_usage.monthly_cost_limit
            and profile.llm_usage.monthly_cost_limit > 0
        ):
            cost_limit_percentage = min(
                100.0,
                (
                    profile.llm_usage.current_month_cost
                    / profile.llm_usage.monthly_cost_limit
                )
                * 100,
            )

        # Return simplified summary
        return {
            "total_tokens": profile.llm_usage.total_tokens,
            "total_cost": profile.llm_usage.total_cost,
            "current_month_tokens": profile.llm_usage.current_month_tokens,
            "current_month_cost": profile.llm_usage.current_month_cost,
            "monthly_quota": profile.llm_usage.monthly_quota,
            "monthly_cost_limit": profile.llm_usage.monthly_cost_limit,
            "usage_limit_percentage": usage_limit_percentage,
            "cost_limit_percentage": cost_limit_percentage,
            "model_count": len(profile.llm_usage.usage_by_model),
            "operation_count": len(profile.llm_usage.usage_by_operation),
        }

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        logger.error(f"Error getting LLM usage summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLM usage summary: {str(e)}",
        )


@router.put("/me/preferences/prompt", response_model=Profile)
async def update_my_prompt_preferences(
    preferences_data: PromptPreferencesUpdate,
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
) -> Profile:
    """Update the current user's prompt preferences.

    Args:
        preferences_data: Prompt preferences data (partial updates allowed)
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Updated profile response
    """
    try:
        # Use the service layer to handle the update logic
        updated_prefs = await profile_service.update_prompt_preferences(
            user_id=current_user.id,
            update_data=preferences_data.model_dump(exclude_unset=True),
        )
        if updated_prefs is None:
            # This might happen if the profile wasn't found or another error occurred
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update prompt preferences.",
            )

        # Return the full updated profile
        updated_profile = await profile_service.get_profile_by_user_id(current_user.id)
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found after update.",
            )  # Should not happen
        return updated_profile

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    except Exception as e:
        logger.error(f"Error updating prompt preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompt preferences: {str(e)}",
        )


@router.put("/me/preferences/system", response_model=Profile)
async def update_my_system_preferences(
    preferences_data: SystemPreferencesUpdate,
    current_user: CurrentActiveUser,
    profile_service: ProfileService = Depends(get_profile_service),
) -> Profile:
    """Update the current user's system preferences.

    Args:
        preferences_data: System preferences data (partial updates allowed)
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Updated profile response
    """
    try:
        # Use the service layer to handle the update logic
        updated_prefs = await profile_service.update_system_preferences(
            user_id=current_user.id,
            update_data=preferences_data.model_dump(exclude_unset=True),
        )
        if updated_prefs is None:
            # This might happen if the profile wasn't found or another error occurred
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update system preferences.",
            )

        # Return the full updated profile
        updated_profile = await profile_service.get_profile_by_user_id(current_user.id)
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found after update.",
            )  # Should not happen
        return updated_profile

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    except Exception as e:
        logger.error(f"Error updating system preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system preferences: {str(e)}",
        )
