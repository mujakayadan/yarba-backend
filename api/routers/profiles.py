"""Profile router for the API."""

from typing import Optional

from beanie import PydanticObjectId
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from api.dependencies.auth import get_current_active_user
from api.dependencies.services import get_profile_service
from core.exceptions.base import NotFoundException
from core.models.profile import PersonalInformation, Preferences, Profile
from core.models.user import User
from core.services.profile_service import ProfileService

router = APIRouter()


class PersonalInfoCreate(BaseModel):
    """Schema for creating personal information."""

    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class ProfileCreate(BaseModel):
    """Schema for creating a profile."""

    personal_information: PersonalInfoCreate
    preferences: Optional[dict] = None


class PersonalInfoUpdate(BaseModel):
    """Schema for updating personal information."""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Schema for updating a profile."""

    personal_information: Optional[PersonalInfoUpdate] = None


class PreferencesUpdate(BaseModel):
    """Schema for updating preferences."""

    project_details: Optional[dict] = None
    work_experience_details: Optional[dict] = None
    skills_details: Optional[dict] = None
    career_summary_details: Optional[dict] = None
    education_details: Optional[dict] = None
    cover_letter_details: Optional[dict] = None
    awards_details: Optional[dict] = None
    publications_details: Optional[dict] = None
    feature_preferences: Optional[dict] = None
    notifications: Optional[dict] = None
    privacy: Optional[dict] = None
    llm_preferences: Optional[dict] = None
    section_preferences: Optional[dict] = None


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
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """
    Get the current user's profile.

    Args:
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Profile
    """
    try:
        profile = await profile_service.get_profile_by_user_id(current_user.id)
        return profile
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """
    Create a new profile.

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
        preferences = None
        if profile_data.preferences:
            preferences = Preferences(**profile_data.preferences)
        else:
            preferences = Preferences()

        # Create personal information
        personal_information = PersonalInformation(
            **profile_data.personal_information.model_dump()
        )

        # Create profile
        profile = Profile(
            user_id=current_user.id,
            personal_information=personal_information,
            preferences=preferences,
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
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """
    Update the current user's profile.

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
                    profile_id=profile.id,
                    personal_information=personal_info_data,
                )
                # Refresh profile
                profile = await profile_service.get_profile_by_id(profile.id)

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


@router.put("/me/preferences", response_model=Profile)
async def update_my_preferences(
    preferences_data: PreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """
    Update the current user's preferences.

    Args:
        preferences_data: Preferences data
        current_user: Current authenticated user
        profile_service: Profile service

    Returns:
        Updated profile
    """
    try:
        # Get existing profile
        profile = await profile_service.get_profile_by_user_id(current_user.id)

        # Create preferences if not exists
        if not profile.preferences:
            profile.preferences = Preferences()

        # Update preferences fields
        for field, value in preferences_data.model_dump(exclude_unset=True).items():
            if value is not None:
                if not hasattr(profile.preferences, field):
                    setattr(profile.preferences, field, {})

                # Update nested dictionary
                current_value = getattr(profile.preferences, field)
                if isinstance(current_value, dict) and isinstance(value, dict):
                    current_value.update(value)
                else:
                    setattr(profile.preferences, field, value)

        # Save through service
        updated_profile = await profile_service.update_profile(profile)
        return updated_profile
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}",
        )


@router.get("/{profile_id}", response_model=Profile)
async def get_profile(
    profile_id: str = Path(..., description="Profile ID"),
    current_user: User = Depends(get_current_active_user),
    profile_service: ProfileService = Depends(get_profile_service),
):
    """
    Get a profile by ID.

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
