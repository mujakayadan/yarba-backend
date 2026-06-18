"""Job application logging and prepare orchestration."""

from datetime import UTC, datetime
from urllib.parse import urlparse

from beanie import PydanticObjectId

from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.job_application import APPLICATION_STATUSES, JobApplication
from core.models.resume import Resume
from core.repositories.job_application_repository import JobApplicationRepository
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.schemas.application_schemas import ApplicationProfile
from core.services.application_profile_service import ApplicationProfileService
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.cover_letter_service import CoverLetterService
from core.services.job_service import JobService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService
from core.services.resume_with_pdf_orchestrator import create_resume_with_pdf
from core.utils.object_id import require_object_id

logger = get_logger(__name__)


def detect_platform(job_url: str | None) -> str | None:
    if not job_url:
        return None
    domain = urlparse(job_url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


class JobApplicationService:
    """CRUD and prepare flow for job application records."""

    def __init__(
        self,
        application_repository: JobApplicationRepository,
        application_profile_service: ApplicationProfileService,
        profile_repository: ProfileRepository,
        portfolio_repository: PortfolioRepository,
        resume_service: ResumeService,
        resume_generation_service: ResumeGenerationService,
        job_service: JobService,
        cover_letter_service: CoverLetterService | None = None,
        cover_letter_generation_service: CoverLetterGenerationService | None = None,
    ) -> None:
        self.application_repository = application_repository
        self.application_profile_service = application_profile_service
        self.profile_repository = profile_repository
        self.portfolio_repository = portfolio_repository
        self.resume_service = resume_service
        self.resume_generation_service = resume_generation_service
        self.job_service = job_service
        self.cover_letter_service = cover_letter_service
        self.cover_letter_generation_service = cover_letter_generation_service
        self.logger = get_logger(self.__class__.__name__)

    async def create(
        self,
        *,
        user_id: PydanticObjectId,
        job_url: str | None = None,
        company_name: str | None = None,
        job_title: str | None = None,
        resume_id: PydanticObjectId | None = None,
        cover_letter_id: PydanticObjectId | None = None,
        status: str = "draft",
        metadata: dict | None = None,
    ) -> JobApplication:
        if status not in APPLICATION_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        record = JobApplication(
            user_id=user_id,
            job_url=job_url,
            company_name=company_name,
            job_title=job_title,
            platform=detect_platform(job_url),
            resume_id=resume_id,
            cover_letter_id=cover_letter_id,
            status=status,
            metadata=metadata or {},
        )
        return await self.application_repository.create(record)

    async def get(
        self, application_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> JobApplication:
        record = await self.application_repository.get_by_id(application_id)
        if not record or record.user_id != user_id:
            raise NotFoundException(f"Application {application_id} not found")
        return record

    async def list(
        self,
        user_id: PydanticObjectId,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[JobApplication], int]:
        items = await self.application_repository.list_by_user(
            user_id, status=status, skip=skip, limit=limit
        )
        total = await self.application_repository.count_by_user(user_id, status=status)
        return items, total

    async def update_status(
        self,
        application_id: PydanticObjectId,
        user_id: PydanticObjectId,
        *,
        status: str,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> JobApplication:
        if status not in APPLICATION_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        record = await self.get(application_id, user_id)
        record.status = status
        record.error_message = error_message
        record.updated_at = datetime.now(UTC)
        if status == "submitted":
            record.submitted_at = datetime.now(UTC)
        if metadata:
            record.metadata = {**record.metadata, **metadata}
        await record.save()
        return record

    async def prepare(
        self,
        *,
        user_id: PydanticObjectId,
        job_url: str | None,
        job_description: str | None,
        compile_pdf: bool = True,
        generate_cover_letter: bool = False,
        scopes: set[str] | None = None,
    ) -> tuple[JobApplication, ApplicationProfile, Resume]:
        if not job_url and not job_description:
            raise ValueError("job_url or job_description is required")

        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise NotFoundException("Profile not found")
        portfolio = await self.portfolio_repository.get_by_user_id(user_id)
        if not portfolio:
            raise NotFoundException("Portfolio not found")

        description = job_description or ""
        if job_url and not description:
            job_details = await self.job_service.extract_job_details_from_url(job_url)
            if job_details and job_details.description:
                description = job_details.description

        if not description.strip():
            raise NotFoundException("Could not resolve job description")

        resume, _pdf_bytes = await create_resume_with_pdf(
            user_id=user_id,
            profile_id=require_object_id(profile.id),
            portfolio_id=require_object_id(portfolio.id),
            job_description=description,
            job_description_url=job_url,
            profile=profile,
            resume_service=self.resume_service,
            resume_generation_service=self.resume_generation_service,
            compile_pdf=compile_pdf,
        )

        cover_letter_id = None
        if (
            generate_cover_letter
            and self.cover_letter_service
            and self.cover_letter_generation_service
        ):
            cover_letter = await self.cover_letter_service.create_cover_letter(
                user_id=user_id,
                resume_id=require_object_id(resume.id),
                profile_id=resume.profile_id,
                portfolio_id=resume.portfolio_id,
            )
            await self.cover_letter_generation_service.generate_cover_letter_content(
                cover_letter_id=require_object_id(cover_letter.id)
            )
            cover_letter_id = require_object_id(cover_letter.id)

        application = await self.create(
            user_id=user_id,
            job_url=job_url,
            company_name=resume.company_name,
            job_title=resume.job_title,
            resume_id=require_object_id(resume.id),
            cover_letter_id=cover_letter_id,
            status="preview_ready",
        )

        app_profile = await self.application_profile_service.build(
            user_id=user_id,
            resume_id=require_object_id(resume.id),
            cover_letter_id=cover_letter_id,
            job_url=job_url,
            scopes=scopes,
        )
        return application, app_profile, resume
