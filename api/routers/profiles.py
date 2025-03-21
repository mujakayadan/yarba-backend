"""Profile router for the API."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, EmailStr

from core.database import get_profile_repository
from core.models.profile import Preferences, Profile
from core.models.user import User
from core.repositories.profile_repository import ProfileRepository

from ..dependencies.auth import get_current_active_user

router = APIRouter()


class ProfileCreate(BaseModel):
    """Schema for creating a profile."""

    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[dict] = None


class ProfileUpdate(BaseModel):
    """Schema for updating a profile."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    bio: Optional[str] = None


class PreferencesUpdate(BaseModel):
    """Schema for updating preferences."""

    project_details: Optional[dict] = None
    work_experience: Optional[dict] = None
    skills: Optional[dict] = None
    career_summary: Optional[dict] = None
    education: Optional[dict] = None
    cover_letter: Optional[dict] = None
    awards: Optional[dict] = None
    publications: Optional[dict] = None
    feature_preferences: Optional[dict] = None
    notification_preferences: Optional[dict] = None
    privacy_preferences: Optional[dict] = None
    llm_preferences: Optional[dict] = None
    section_preferences: Optional[dict] = None


@router.get("/me", response_model=Profile)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    profile_repository: ProfileRepository = Depends(get_profile_repository),
):
    """
    Get the current user's profile.

    Args:
        current_user: Current authenticated user
        profile_repository: Profile repository

    Returns:
        Profile
    """
    profile = await profile_repository.get_by_user(current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return profile


@router.post("/", response_model=Profile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_active_user),
    profile_repository: ProfileRepository = Depends(get_profile_repository),
):
    """
    Create a new profile.

    Args:
        profile_data: Profile data
        current_user: Current authenticated user
        profile_repository: Profile repository

    Returns:
        Created profile
    """
    # Check if the user already has a profile
    existing_profile = await profile_repository.get_by_user(current_user)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile",
        )

    # Create preferences if provided
    preferences = None
    if profile_data.preferences:
        preferences = Preferences(**profile_data.preferences)

    # Create profile
    profile = Profile(
        user_id=current_user.id,
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        email=profile_data.email,
        phone=profile_data.phone,
        location=profile_data.location,
        website=profile_data.website,
        github=profile_data.github,
        linkedin=profile_data.linkedin,
        twitter=profile_data.twitter,
        bio=profile_data.bio,
        preferences=preferences,
    )

    await profile.create()
    return profile


@router.put("/me", response_model=Profile)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    profile_repository: ProfileRepository = Depends(get_profile_repository),
):
    """
    Update the current user's profile.

    Args:
        profile_data: Profile data
        current_user: Current authenticated user
        profile_repository: Profile repository

    Returns:
        Updated profile
    """
    profile = await profile_repository.get_by_user(current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Update profile fields
    for field, value in profile_data.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    await profile.save()
    return profile


@router.put("/me/preferences", response_model=Profile)
async def update_my_preferences(
    preferences_data: PreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    profile_repository: ProfileRepository = Depends(get_profile_repository),
):
    """
    Update the current user's preferences.

    Args:
        preferences_data: Preferences data
        current_user: Current authenticated user
        profile_repository: Profile repository

    Returns:
        Updated profile
    """
    profile = await profile_repository.get_by_user(current_user)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Create preferences if not exists
    if not profile.preferences:
        profile.preferences = Preferences()

    # Update preferences fields
    for field, value in preferences_data.dict(exclude_unset=True).items():
        if value is not None:
            if not hasattr(profile.preferences, field):
                setattr(profile.preferences, field, {})

            # Update nested dictionary
            current_value = getattr(profile.preferences, field)
            if isinstance(current_value, dict) and isinstance(value, dict):
                current_value.update(value)
            else:
                setattr(profile.preferences, field, value)

    # Save profile
    await profile.save()
    return profile


@router.get("/{profile_id}", response_model=Profile)
async def get_profile(
    profile_id: str = Path(..., description="Profile ID"),
    current_user: User = Depends(get_current_active_user),
    profile_repository: ProfileRepository = Depends(get_profile_repository),
):
    """
    Get a profile by ID.

    Args:
        profile_id: Profile ID
        current_user: Current authenticated user
        profile_repository: Profile repository

    Returns:
        Profile
    """
    profile = await profile_repository.get_by_id(profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Check if the profile belongs to the current user
    if profile.user_id != current_user.id:
        # Check if the profile is public
        if (
            not profile.preferences
            or not profile.preferences.privacy_preferences
            or profile.preferences.privacy_preferences.get("profile_visibility")
            != "public"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this profile",
            )

    return profile
