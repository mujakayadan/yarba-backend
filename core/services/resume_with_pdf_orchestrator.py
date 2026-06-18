"""Shared orchestration: create resume, generate content, compile and store PDF."""

from beanie import PydanticObjectId

from api.schemas.resume import ResumeUpdate
from config.logging_config import get_logger
from core.exceptions.base import InternalServerException
from core.models.profile import Profile
from core.models.resume import Resume
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService
from core.utils.object_id import require_object_id
from utils.storage import get_storage_provider

logger = get_logger(__name__)


async def create_resume_with_pdf(
    *,
    user_id: PydanticObjectId,
    profile_id: PydanticObjectId,
    portfolio_id: PydanticObjectId,
    job_description: str,
    job_description_url: str | None,
    profile: Profile,
    resume_service: ResumeService,
    resume_generation_service: ResumeGenerationService,
    compile_pdf: bool = True,
) -> tuple[Resume, bytes]:
    """Create a resume, generate LLM content, compile PDF, and persist storage key."""
    resume = await resume_service.create_resume(
        user_id=user_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
        job_description=job_description,
        job_description_url=job_description_url,
    )
    await resume_generation_service.generate_resume_textual_content(
        resume_id=require_object_id(resume.id)
    )
    resume_with_content = await resume_service.get_resume_by_id(
        require_object_id(resume.id), user_id
    )
    if not resume_with_content or not resume_with_content.content:
        raise InternalServerException(
            f"Failed to populate resume content for {resume.id}"
        )

    if not compile_pdf:
        return resume_with_content, b""

    pdf_bytes = await resume_generation_service.compile_pdf(
        resume_with_content, profile
    )
    if not pdf_bytes:
        raise InternalServerException(f"Failed to compile PDF for resume {resume.id}")

    storage_provider = get_storage_provider()
    pdf_key = await storage_provider.save_resume_pdf(pdf_bytes, str(resume.id))
    update_data = ResumeUpdate(resume_pdf_key=pdf_key)
    updated = await resume_service.update_resume(
        resume_id=require_object_id(resume.id),
        user_id=user_id,
        update_data=update_data.model_dump(exclude_unset=True),
    )
    if not updated:
        raise InternalServerException(
            f"Failed to update resume {resume.id} with PDF key"
        )
    return updated, pdf_bytes
