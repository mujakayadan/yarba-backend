"""Profile model for MongoDB using Beanie ODM."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field, EmailStr

from .user import User


class Preferences(BaseModel):
    """User preferences model."""

    # Project preferences
    project_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_projects": 4, "bullet_points_per_project": 3}
    )

    # Work experience preferences
    work_experience_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_jobs": 4, "bullet_points_per_job": 3}
    )

    # Skills preferences
    skills_details: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_categories": 5,
            "min_skills_per_category": 3,
            "max_skills_per_category": 10,
        }
    )

    # Career summary preferences
    career_summary_details: Dict[str, Any] = Field(
        default_factory=lambda: {"min_words": 15, "max_words": 25}
    )

    # Education preferences
    education_details: Dict[str, Any] = Field(
        default_factory=lambda: {"max_entries": 3, "max_courses": 4}
    )

    # Other section preferences
    cover_letter_details: Dict[str, Any] = Field(default_factory=dict)
    awards_details: Dict[str, Any] = Field(default_factory=dict)
    publications_details: Dict[str, Any] = Field(default_factory=dict)

    # Feature preferences
    feature_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "check_clearance": True,
            "auto_save": True,
            "dark_mode": False,
        }
    )

    # Notification preferences
    notifications: Dict[str, Any] = Field(default_factory=dict)

    # Privacy preferences
    privacy: Dict[str, Any] = Field(default_factory=dict)

    # LLM preferences
    llm_preferences: Dict[str, Any] = Field(
        default_factory=lambda: {
            "model_type": "Claude",
            "model_name": "claude-3-5-sonnet-20240620",
            "temperature": 0.1,
        }
    )

    # Section processing preferences
    section_preferences: Dict[str, str] = Field(
        default_factory=lambda: {
            "personal_information": "Hardcode",
            "career_summary": "Process",
            "skills": "Process",
            "work_experience": "Process",
            "education": "Process",
            "projects": "Process",
            "awards": "Hardcode",
            "publications": "Hardcode",
        }
    )

    model_config = {"validate_assignment": True}


class Profile(Document):
    """Profile model for MongoDB using Beanie ODM."""

    user_id: PydanticObjectId
    user: Optional[Link[User]] = None

    # Personal information
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None

    # Additional information
    signature: Optional[bytes] = None
    life_story: Optional[str] = None

    # User preferences
    preferences: Preferences = Field(default_factory=Preferences)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "validate_assignment": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda x: x.isoformat(),
        },
    }

    class Settings:
        """Beanie document settings."""

        name = "profiles"
        use_state_management = True
        bson_encoders = {
            datetime: lambda x: x,
        }

    async def get_user(self):
        """Get the user associated with this profile."""
        if not self.user:
            self.user = await User.get(self.user_id)
        return self.user

    async def get_resumes(self):
        """Get all resumes that use this profile."""
        from .resume import Resume

        return await Resume.find(Resume.profile_id == self.id).to_list()

    def migrate_personal_info(self):
        """Migrate personal information from the personal_information field to individual fields."""
        if not self.personal_information:
            return

        if "full_name" in self.personal_information and not self.full_name:
            self.full_name = self.personal_information.get("full_name", "")

        if "email" in self.personal_information and not self.email:
            self.email = self.personal_information.get("email", "")

        if "phone" in self.personal_information and not self.phone:
            self.phone = self.personal_information.get("phone", None)

        if "address" in self.personal_information and not self.address:
            self.address = self.personal_information.get("address", None)

        if "linkedin" in self.personal_information and not self.linkedin:
            self.linkedin = self.personal_information.get("linkedin", None)

        if "github" in self.personal_information and not self.github:
            self.github = self.personal_information.get("github", None)

        if "website" in self.personal_information and not self.website:
            self.website = self.personal_information.get("website", None)
