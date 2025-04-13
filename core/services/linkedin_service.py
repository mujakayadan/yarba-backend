# """LinkedIn service for authentication and job application."""

# import os
# from datetime import datetime, timezone
# from typing import Any, Dict, List, Optional, Tuple

# from beanie import PydanticObjectId
# from cryptography.fernet import Fernet
# from pydantic import EmailStr

# from config.constants import FEATURE_FLAGS
# from config.logging_config import get_logger
# from config.settings import settings
# from core.easy_applier.job_applier import JobApplier
# from core.easy_applier.job_extractor import JobExtractor
# from core.easy_applier.linkedin_job_manager import LinkedInJobManager

# # Import the easy_applier components
# from core.easy_applier.linkedin_scraper import LinkedInScraper
# from core.exceptions.base import NotFoundException, OperationFailedException
# from core.models.user import User
# from core.repositories.resume_repository import ResumeRepository
# from core.services.resume_service import ResumeService

# logger = get_logger(__name__)


# class LinkedInService:
#     """Service for LinkedIn operations including job applications."""

#     def __init__(
#         self,
#         resume_repository: Optional[ResumeRepository] = None,
#         resume_service: Optional[ResumeService] = None,
#     ):
#         """Initialize the LinkedIn service."""
#         self.logger = get_logger(self.__class__.__name__)
#         self.resume_repository = resume_repository or ResumeRepository()
#         self.resume_service = resume_service or ResumeService(
#             resume_repository=self.resume_repository
#         )
#         self._scraper = None
#         self._job_applier = None
#         self._job_manager = None

#         # Create cipher for encrypting LinkedIn passwords
#         # In production, this key should be stored securely outside the codebase
#         # and should be unique per environment
#         linkedin_key = os.environ.get(
#             "LINKEDIN_ENCRYPTION_KEY", settings.auth.jwt_secret_key.get_secret_value()
#         )
#         if isinstance(linkedin_key, str) and len(linkedin_key) >= 32:
#             # Use first 32 bytes as key
#             key = linkedin_key[:32].encode().ljust(32, b"=")
#         else:
#             # Fallback - not recommended for production
#             key = b"JD38dfj3IDFJf93jfie93jf93jfFJDSk_="

#         self.cipher = Fernet(Fernet.generate_key())

#     async def save_credentials(
#         self, user: User, linkedin_email: EmailStr, linkedin_password: str
#     ) -> bool:
#         """
#         Save LinkedIn credentials for a user.

#         Args:
#             user: User document
#             linkedin_email: LinkedIn email address
#             linkedin_password: LinkedIn password (will be encrypted)

#         Returns:
#             bool: True if credentials were saved successfully
#         """
#         try:
#             # Check if LinkedIn integration is enabled
#             if not FEATURE_FLAGS.get("linkedin_integration", False):
#                 self.logger.warning("LinkedIn integration is disabled in feature flags")
#                 return False

#             # Encrypt the password
#             encrypted_password = self.cipher.encrypt(
#                 linkedin_password.encode()
#             ).decode()

#             # Store the encrypted password in a separate, secure collection
#             # In a production environment, consider using a dedicated secrets manager
#             linkedin_auth = {
#                 "user_id": user.id,
#                 "email": linkedin_email,
#                 "encrypted_password": encrypted_password,
#             }

#             # TODO: Store linkedin_auth in a separate secure collection
#             # For now, we'll continue to use the user model as a placeholder
#             # but we're not storing the actual password there

#             # Update user document with LinkedIn settings (but not the password)
#             user.linkedin_email = linkedin_email
#             user.linkedin_integration_enabled = True
#             user.linkedin_last_login = datetime.now(timezone.utc)

#             await user.save()
#             self.logger.info(f"LinkedIn credentials saved for user {user.id}")
#             return True
#         except Exception as e:
#             self.logger.error(f"Error saving LinkedIn credentials: {str(e)}")
#             return False

#     # The verify_credentials method is not needed anymore as we'll decrypt and use
#     # the password directly when needed

#     async def search_jobs(
#         self, user: User, keywords: str, location: str, num_jobs: int = 10
#     ) -> List[Dict[str, Any]]:
#         """
#         Search for jobs on LinkedIn.

#         Args:
#             user: User document
#             keywords: Job search keywords
#             location: Job search location
#             num_jobs: Number of jobs to search for

#         Returns:
#             List of job descriptions
#         """
#         if not user.linkedin_integration_enabled or not user.linkedin_email:
#             raise OperationFailedException(
#                 "LinkedIn integration not enabled for this user"
#             )

#         # For now, in development, use the global LinkedIn password
#         # In production, you would retrieve and decrypt the user's stored credential
#         linkedin_password = settings.linkedin_password
#         linkedin_email = user.linkedin_email

#         # Initialize scraper and job manager
#         try:
#             scraper = self._get_or_create_scraper(linkedin_email, linkedin_password)
#             job_manager = self._get_or_create_job_manager(scraper)

#             # Search for jobs
#             job_descriptions = job_manager.search_and_get_job_descriptions(
#                 keywords, location, num_jobs
#             )

#             if not job_descriptions:
#                 self.logger.warning(f"No jobs found for {keywords} in {location}")
#                 return []

#             self.logger.info(
#                 f"Found {len(job_descriptions)} jobs for {keywords} in {location}"
#             )
#             return job_descriptions

#         except Exception as e:
#             self.logger.error(f"Error searching for jobs: {str(e)}")
#             raise OperationFailedException(f"Failed to search for jobs: {str(e)}")

#     async def apply_for_job(
#         self, user: User, job_url: str, resume_id: PydanticObjectId
#     ) -> Dict[str, Any]:
#         """
#         Apply for a job on LinkedIn using the user's credentials.

#         Args:
#             user: User document
#             job_url: LinkedIn job URL to apply for
#             resume_id: ID of the resume to use for the application

#         Returns:
#             Dict containing result of the application
#         """
#         if not user.linkedin_integration_enabled or not user.linkedin_email:
#             raise OperationFailedException(
#                 "LinkedIn integration not enabled for this user"
#             )

#         # Get resume from database
#         resume = await self.resume_repository.get_by_id(resume_id)
#         if not resume:
#             raise NotFoundException(f"Resume with ID {resume_id} not found")

#         # Generate PDF for the resume
#         pdf_path = await self.resume_service.generate_pdf(resume_id)
#         if not pdf_path or not os.path.exists(pdf_path):
#             raise OperationFailedException("Failed to generate resume PDF")

#         # Get LinkedIn credentials
#         linkedin_password = settings.linkedin_password
#         linkedin_email = user.linkedin_email

#         # Initialize scraper and job applier
#         try:
#             scraper = self._get_or_create_scraper(linkedin_email, linkedin_password)
#             job_applier = self._get_or_create_job_applier(scraper)

#             # Apply for the job
#             success = await job_applier.apply_to_job(job_url, pdf_path)

#             result = {
#                 "success": success,
#                 "job_url": job_url,
#                 "resume_id": str(resume_id),
#                 "timestamp": datetime.now(timezone.utc).isoformat(),
#             }

#             self.logger.info(
#                 f"Job application {'successful' if success else 'failed'} for user {user.id} and job {job_url}"
#             )

#             return result

#         except Exception as e:
#             self.logger.error(f"Error applying for job: {str(e)}")
#             raise OperationFailedException(f"Failed to apply for job: {str(e)}")

#     async def apply_for_jobs(
#         self, user: User, job_urls: List[str], resume_id: PydanticObjectId
#     ) -> Dict[str, Any]:
#         """
#         Apply for multiple jobs on LinkedIn using the user's credentials.

#         Args:
#             user: User document
#             job_urls: List of LinkedIn job URLs to apply for
#             resume_id: ID of the resume to use for applications

#         Returns:
#             Dict containing results of the applications
#         """
#         if not user.linkedin_integration_enabled or not user.linkedin_email:
#             raise OperationFailedException(
#                 "LinkedIn integration not enabled for this user"
#             )

#         # Get resume from database
#         resume = await self.resume_repository.get_by_id(resume_id)
#         if not resume:
#             raise NotFoundException(f"Resume with ID {resume_id} not found")

#         # Generate PDF for the resume
#         pdf_path = await self.resume_service.generate_pdf(resume_id)
#         if not pdf_path or not os.path.exists(pdf_path):
#             raise OperationFailedException("Failed to generate resume PDF")

#         # Initialize results tracking
#         results = {
#             "successful": [],
#             "failed": [],
#             "total": len(job_urls),
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#         }

#         # Get LinkedIn credentials
#         linkedin_password = settings.linkedin_password
#         linkedin_email = user.linkedin_email

#         # Initialize scraper and job applier
#         try:
#             scraper = self._get_or_create_scraper(linkedin_email, linkedin_password)
#             job_applier = self._get_or_create_job_applier(scraper)

#             # Apply for each job
#             for job_url in job_urls:
#                 try:
#                     success = await job_applier.apply_to_job(job_url, pdf_path)

#                     if success:
#                         results["successful"].append(
#                             {
#                                 "job_url": job_url,
#                                 "timestamp": datetime.now(timezone.utc).isoformat(),
#                             }
#                         )
#                     else:
#                         results["failed"].append(
#                             {
#                                 "job_url": job_url,
#                                 "error": "Application failed",
#                                 "timestamp": datetime.now(timezone.utc).isoformat(),
#                             }
#                         )

#                 except Exception as e:
#                     self.logger.error(f"Error applying for job {job_url}: {str(e)}")
#                     results["failed"].append(
#                         {
#                             "job_url": job_url,
#                             "error": str(e),
#                             "timestamp": datetime.now(timezone.utc).isoformat(),
#                         }
#                     )

#             self.logger.info(
#                 f"Applied to {len(results['successful'])} jobs successfully, "
#                 f"{len(results['failed'])} failed for user {user.id}"
#             )

#             return results

#         except Exception as e:
#             self.logger.error(f"Error applying for jobs: {str(e)}")
#             raise OperationFailedException(f"Failed to apply for jobs: {str(e)}")

#     def _get_or_create_scraper(self, email: str, password: str) -> LinkedInScraper:
#         """Get or create a LinkedIn scraper instance."""
#         if not self._scraper:
#             try:
#                 self._scraper = LinkedInScraper(
#                     email=email,
#                     password=password,
#                     profile_name="Resume Builder",
#                     headless=False,
#                 )
#             except Exception as e:
#                 self.logger.error(f"Error creating LinkedIn scraper: {str(e)}")
#                 raise OperationFailedException(
#                     f"Failed to initialize LinkedIn connection: {str(e)}"
#                 )
#         return self._scraper

#     def _get_or_create_job_applier(self, scraper: LinkedInScraper) -> JobApplier:
#         """Get or create a job applier instance."""
#         if not self._job_applier:
#             from core.database.factory import get_unit_of_work

#             unit_of_work = get_unit_of_work()
#             self._job_applier = JobApplier(scraper.driver, unit_of_work)
#         return self._job_applier

#     def _get_or_create_job_manager(
#         self, scraper: LinkedInScraper
#     ) -> LinkedInJobManager:
#         """Get or create a job manager instance."""
#         if not self._job_manager:
#             job_applier = self._get_or_create_job_applier(scraper)

#             # For job manager, we need a resume generator
#             # This is a placeholder - you'll need to adapt this to your specific setup
#             from core.database.factory import get_unit_of_work

#             unit_of_work = get_unit_of_work()

#             # Replace this with your actual resume generator implementation
#             from core.repositories.portfolio_repository import PortfolioRepository
#             from core.repositories.profile_repository import ProfileRepository
#             from core.services.resume_generation_service import ResumeGenerationService

#             resume_generator = ResumeGenerationService(
#                 resume_repository=self.resume_repository,
#                 portfolio_repository=PortfolioRepository(),
#                 profile_repository=ProfileRepository(),
#             )

#             self._job_manager = LinkedInJobManager(
#                 scraper=scraper,
#                 job_applier=job_applier,
#                 resume_generator=resume_generator,
#                 unit_of_work=unit_of_work,
#             )
#         return self._job_manager

#     def close(self):
#         """Close the LinkedIn scraper."""
#         if self._scraper:
#             try:
#                 self._scraper.close()
#                 self._scraper = None
#                 self._job_applier = None
#                 self._job_manager = None
#             except Exception as e:
#                 self.logger.error(f"Error closing LinkedIn scraper: {str(e)}")
