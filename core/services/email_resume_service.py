"""Orchestrate resume generation from inbound email and outbound PDF delivery."""

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from api.schemas.resume import ResumeUpdate
from config.logging_config import get_logger
from config.settings import settings
from core.exceptions.base import InternalServerException
from core.job_extractor.extract_job import JobExtractor
from core.models.inbound_email import InboundEmail
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from core.services.email_clients.resend_client import ResendClient
from core.services.job_service import JobService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import (
    ClearanceRequiredException,
    ResumeGenerationService,
)
from core.services.resume_service import ResumeService
from core.utils.email_body_parser import extract_job_description
from core.utils.object_id import require_object_id
from core.utils.resume_pdf_filename import build_resume_pdf_filename
from utils.storage import get_storage_provider

logger = get_logger(__name__)


def _generic_generation_error() -> str:
    return (
        "We ran into an error while generating your resume.\n\n"
        "Please try again in a few minutes. If the problem persists, "
        f"create the resume in the app at {settings.frontend_url}."
    )


class EmailResumeService:
    """Process inbound job emails and reply with tailored resume PDFs."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        profile_service: ProfileService,
        portfolio_service: PortfolioService,
        resume_service: ResumeService,
        resume_generation_service: ResumeGenerationService,
        resend_client: ResendClient,
    ) -> None:
        self.user_repository = user_repository
        self.profile_service = profile_service
        self.portfolio_service = portfolio_service
        self.resume_service = resume_service
        self.resume_generation_service = resume_generation_service
        self.resend_client = resend_client
        self.logger = logger

    async def claim_inbound_email(self, email_id: str, sender_email: str) -> bool:
        """Record inbound email; return False if already processed."""
        existing = await InboundEmail.find_one(InboundEmail.email_id == email_id)
        if existing:
            return False
        try:
            await InboundEmail(email_id=email_id, sender_email=sender_email).insert()
            return True
        except DuplicateKeyError:
            return False

    async def mark_inbound_status(self, email_id: str, status: str) -> None:
        record = await InboundEmail.find_one(InboundEmail.email_id == email_id)
        if record:
            record.status = status
            await record.save()

    async def process_inbound_email(self, email_id: str) -> None:
        """Fetch inbound email, generate resume, and reply with PDF."""
        existing = await InboundEmail.find_one(InboundEmail.email_id == email_id)
        if existing:
            self.logger.info("Skipping duplicate inbound email %s", email_id)
            return

        received = await self.resend_client.get_received_email(email_id)
        sender = received.from_.strip().lower()

        if not await self.claim_inbound_email(email_id, sender):
            return

        subject = received.subject or "Job application"
        try:
            job_description = extract_job_description(received.text, received.html)
        except ValueError:
            await self._send_error(
                sender,
                subject,
                (
                    "We could not find enough job description text in your email.\n\n"
                    "Please forward the full recruiter message (including the job "
                    "description) to resumes@yarba.app and try again."
                ),
            )
            await self.mark_inbound_status(email_id, "failed")
            return

        user = await self.user_repository.get_by_email_insensitive(sender)
        if not user or not user.id:
            await self._send_error(
                sender,
                subject,
                (
                    f"No YARBA account found for {sender}.\n\n"
                    f"Register at {settings.frontend_url} using this email address, "
                    "then forward the job description again."
                ),
            )
            await self.mark_inbound_status(email_id, "failed")
            return

        user_id = require_object_id(user.id)
        profile = await self.profile_service.get_profile_by_user_id(user_id)
        if not profile:
            await self._send_error(
                sender,
                subject,
                (
                    "Your YARBA profile is not set up yet.\n\n"
                    f"Complete your profile at {settings.frontend_url}, then forward "
                    "the job description again."
                ),
            )
            await self.mark_inbound_status(email_id, "failed")
            return

        portfolio = await self.portfolio_service.get_portfolio_by_user_id(user_id)
        if not portfolio:
            await self._send_error(
                sender,
                subject,
                (
                    "Your YARBA portfolio is not set up yet.\n\n"
                    f"Add your portfolio at {settings.frontend_url}, then forward "
                    "the job description again."
                ),
            )
            await self.mark_inbound_status(email_id, "failed")
            return

        try:
            resume, pdf_bytes = await self._create_resume_with_pdf(
                user_id=user_id,
                profile_id=require_object_id(profile.id),
                portfolio_id=require_object_id(portfolio.id),
                job_description=job_description,
                profile=profile,
            )
        except ClearanceRequiredException:
            await self._send_error(
                sender,
                subject,
                (
                    "This job description appears to require a security clearance "
                    "or similar restriction that YARBA cannot generate a resume for "
                    "with your current settings.\n\n"
                    f"Review the job posting or adjust settings at {settings.frontend_url}."
                ),
            )
            await self.mark_inbound_status(email_id, "failed")
            return
        except Exception as exc:
            self.logger.error(
                "Email resume generation failed for %s: %s",
                email_id,
                exc,
                exc_info=True,
            )
            await self._send_error(sender, subject, _generic_generation_error())
            await self.mark_inbound_status(email_id, "failed")
            return

        title_parts = [part for part in (resume.company_name, resume.job_title) if part]
        pdf_subject = (
            f"Your YARBA resume — {' / '.join(title_parts)}"
            if title_parts
            else "Your YARBA resume"
        )
        await self.resend_client.send_pdf_attachment(
            to=sender,
            subject=pdf_subject,
            text=(
                "Your tailored resume is attached.\n\n"
                f"You can also view and edit it in your YARBA account at {settings.frontend_url}."
            ),
            pdf_bytes=pdf_bytes,
            filename=build_resume_pdf_filename(
                resume.company_name,
                resume.job_title,
            ),
        )
        await self.mark_inbound_status(email_id, "completed")
        self.logger.info("Sent resume PDF for inbound email %s to %s", email_id, sender)

    async def _create_resume_with_pdf(
        self,
        *,
        user_id: PydanticObjectId,
        profile_id: PydanticObjectId,
        portfolio_id: PydanticObjectId,
        job_description: str,
        profile,
    ) -> tuple[Resume, bytes]:
        resume = await self.resume_service.create_resume(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            job_description=job_description,
        )
        await self.resume_generation_service.generate_resume_textual_content(
            resume_id=require_object_id(resume.id)
        )
        resume_with_content = await self.resume_service.get_resume_by_id(
            require_object_id(resume.id), user_id
        )
        if not resume_with_content or not resume_with_content.content:
            raise InternalServerException(
                f"Failed to populate resume content for {resume.id}"
            )

        pdf_bytes = await self.resume_generation_service.compile_pdf(
            resume_with_content, profile
        )
        if not pdf_bytes:
            raise InternalServerException(
                f"Failed to compile PDF for resume {resume.id}"
            )

        storage_provider = get_storage_provider()
        pdf_key = await storage_provider.save_resume_pdf(pdf_bytes, str(resume.id))
        update_data = ResumeUpdate(resume_pdf_key=pdf_key)
        updated = await self.resume_service.update_resume(
            resume_id=require_object_id(resume.id),
            user_id=user_id,
            update_data=update_data.model_dump(exclude_unset=True),
        )
        if not updated:
            raise InternalServerException(
                f"Failed to update resume {resume.id} with PDF key"
            )
        return updated, pdf_bytes

    async def _send_error(self, to: str, original_subject: str, message: str) -> None:
        try:
            await self.resend_client.send_email(
                to=to,
                subject=f"Re: {original_subject} — YARBA could not generate your resume",
                text=message,
            )
        except Exception as exc:
            self.logger.error("Failed to send error email to %s: %s", to, exc)


def build_email_resume_service() -> EmailResumeService:
    """Construct EmailResumeService with default dependencies (for background tasks)."""
    from core.services.email_clients.resend_client import get_resend_client

    user_repo = UserRepository()
    profile_repo = ProfileRepository()
    portfolio_repo = PortfolioRepository()
    resume_repo = ResumeRepository()
    prompt_service = PromptService()
    profile_service = ProfileService(profile_repo, user_repo)
    portfolio_service = PortfolioService(portfolio_repo, user_repo)
    llm_service = LLMService(profile_repository=profile_repo)
    latex_service = LatexService(portfolio_service=portfolio_service)
    job_service = JobService(
        llm_service=llm_service,
        prompt_service=prompt_service,
        job_extractor=JobExtractor(),
    )
    resume_service = ResumeService(
        user_repository=user_repo,
        resume_repository=resume_repo,
        job_service=job_service,
    )
    resume_generation_service = ResumeGenerationService(
        resume_repository=resume_repo,
        portfolio_repository=portfolio_repo,
        profile_repository=profile_repo,
        prompt_service=prompt_service,
        profile_service=profile_service,
        portfolio_service=portfolio_service,
        llm_service=llm_service,
        latex_service=latex_service,
        job_service=job_service,
    )
    return EmailResumeService(
        user_repository=user_repo,
        profile_service=profile_service,
        portfolio_service=portfolio_service,
        resume_service=resume_service,
        resume_generation_service=resume_generation_service,
        resend_client=get_resend_client(),
    )
