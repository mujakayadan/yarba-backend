"""Build ApplicationProfile payloads for job form autofill."""

from beanie import PydanticObjectId
from pydantic import ValidationError

from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.cover_letter_repository import CoverLetterRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.schemas.application_preferences import Demographics
from core.schemas.application_schemas import ApplicationContact, ApplicationProfile
from core.schemas.resume_schemas import (
    CareerSummarySchema,
    EducationSchema,
    ProjectSchema,
    SkillCategorySchema,
    WorkExperienceSchema,
)
from core.utils.field_encryption import decrypt_json

logger = get_logger(__name__)

DEMOGRAPHICS_READ_SCOPE = "applications:demographics:read"
CREDENTIALS_READ_SCOPE = "applications:credentials:read"


class ApplicationProfileService:
    """Assemble autofill payloads from Profile (PII) and Resume (narrative)."""

    def __init__(
        self,
        resume_repository: ResumeRepository,
        profile_repository: ProfileRepository,
        cover_letter_repository: CoverLetterRepository,
    ) -> None:
        self.resume_repository = resume_repository
        self.profile_repository = profile_repository
        self.cover_letter_repository = cover_letter_repository
        self.logger = get_logger(self.__class__.__name__)

    async def build(
        self,
        *,
        user_id: PydanticObjectId,
        resume_id: PydanticObjectId,
        cover_letter_id: PydanticObjectId | None = None,
        job_url: str | None = None,
        scopes: set[str] | None = None,
    ) -> ApplicationProfile:
        resume = await self.resume_repository.get_by_id(resume_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundException(f"Resume {resume_id} not found")

        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise NotFoundException("Profile not found")

        contact = self._contact_from_profile(profile)
        narrative = self._narrative_from_resume(resume)
        cover_letter_text = await self._cover_letter_text(user_id, cover_letter_id)
        demographics = self._demographics_for_scopes(profile, scopes)
        apply_account_password = self._apply_account_password_for_scopes(
            profile, scopes
        )
        prefs = profile.application_preferences

        return ApplicationProfile(
            contact=contact,
            career_summary=narrative.get("career_summary"),
            work_experience=narrative.get("work_experience", []),
            education=narrative.get("education", []),
            skills=narrative.get("skills", []),
            projects=narrative.get("projects", []),
            cover_letter_text=cover_letter_text,
            resume_id=str(resume_id),
            resume_pdf_download_path=f"/api/v1/resumes/{resume_id}/pdf/download",
            job_url=job_url or resume.job_description_url,
            job_title=resume.job_title,
            company_name=resume.company_name,
            work_eligibility=prefs.work_eligibility,
            logistics=prefs.logistics,
            demographics=demographics,
            apply_account_password=apply_account_password,
        )

    def _contact_from_profile(self, profile: Profile) -> ApplicationContact:
        info = profile.personal_information
        return ApplicationContact(
            full_name=info.full_name,
            email=str(info.email),
            phone=info.phone,
            address=info.address,
            linkedin=info.linkedin,
            github=info.github,
            website=info.website,
        )

    def _narrative_from_resume(self, resume: Resume) -> dict:
        content = resume.content or {}
        result: dict = {
            "work_experience": [],
            "education": [],
            "skills": [],
            "projects": [],
        }
        if summary_raw := content.get("career_summary"):
            try:
                result["career_summary"] = CareerSummarySchema.model_validate(
                    summary_raw
                )
            except ValidationError:
                self.logger.warning("Invalid career_summary on resume %s", resume.id)

        for key, schema in (
            ("work_experience", WorkExperienceSchema),
            ("education", EducationSchema),
            ("skills", SkillCategorySchema),
            ("projects", ProjectSchema),
        ):
            items = content.get(key) or []
            if not isinstance(items, list):
                continue
            parsed = []
            for item in items:
                try:
                    parsed.append(schema.model_validate(item))
                except ValidationError:
                    self.logger.warning(
                        "Skipping invalid %s item on resume %s", key, resume.id
                    )
            result[key] = parsed
        return result

    async def _cover_letter_text(
        self, user_id: PydanticObjectId, cover_letter_id: PydanticObjectId | None
    ) -> str | None:
        if cover_letter_id is None:
            return None
        cover_letter = await self.cover_letter_repository.get_by_id(cover_letter_id)
        if not cover_letter or cover_letter.user_id != user_id:
            return None
        return cover_letter.content

    def _demographics_for_scopes(
        self, profile: Profile, scopes: set[str] | None
    ) -> Demographics | None:
        consent = profile.application_preferences.demographic_consent
        if not consent.consented:
            return None
        if scopes is None or DEMOGRAPHICS_READ_SCOPE not in scopes:
            return None
        if not profile.demographics_encrypted:
            return Demographics()
        data = decrypt_json(profile.demographics_encrypted)
        return Demographics.model_validate(data)

    def _apply_account_password_for_scopes(
        self, profile: Profile, scopes: set[str] | None
    ) -> str | None:
        if not profile.apply_credentials_encrypted:
            return None
        if scopes is not None and CREDENTIALS_READ_SCOPE not in scopes:
            return None
        data = decrypt_json(profile.apply_credentials_encrypted)
        password = data.get("password")
        return password if isinstance(password, str) and password else None
