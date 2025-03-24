"""Service for handling job-related operations."""

from typing import Any, Dict, Optional

from config.constants import APP_CONSTANTS, FEATURE_FLAGS
from config.logging_config import get_logger
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService

logger = get_logger(__name__)


class JobService:
    """Service for extracting and handling job-related information."""

    def __init__(
        self, llm_service: LLMService, prompt_service: Optional[PromptService] = None
    ):
        """
        Initialize JobService.

        Args:
            llm_service: LLM service for text generation
            prompt_service: Prompt service for loading prompts
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.logger = logger

    async def extract_job_info(self, job_description: str) -> Dict[str, Any]:
        """
        Extract basic information from a job description.

        Args:
            job_description: The job description text

        Returns:
            Dictionary containing extracted job information (company_name, job_title)
        """
        try:
            # Use LLM service to extract company name and job title
            company_name, job_title = (
                await self.llm_service.extract_job_title_and_company(job_description)
            )

            # Check for security clearance if feature is enabled
            requires_clearance = False
            if FEATURE_FLAGS.get("check_clearance", False):
                requires_clearance = self.check_security_clearance(job_description)

            # Return the job info dictionary
            return {
                "company_name": company_name,
                "job_title": job_title,
                "job_description": job_description,
                "requires_clearance": requires_clearance,
            }
        except Exception as e:
            self.logger.error(f"Error extracting job info: {str(e)}")
            return {
                "company_name": "unknown_company",
                "job_title": "unknown_position",
                "job_description": job_description,
                "requires_clearance": False,
            }

    def check_security_clearance(self, job_description: str) -> bool:
        """
        Check if the job description requires security clearance.

        Args:
            job_description: The job description text

        Returns:
            bool: True if the job requires security clearance, False otherwise
        """
        try:
            # Convert job description to lowercase for case-insensitive matching
            job_desc_lower = job_description.lower()

            # Check for any security clearance keywords
            for keyword in APP_CONSTANTS.get("clearance_keywords", []):
                if keyword.lower() in job_desc_lower:
                    self.logger.info(f"Found security clearance requirement: {keyword}")
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking security clearance: {str(e)}")
            return False
