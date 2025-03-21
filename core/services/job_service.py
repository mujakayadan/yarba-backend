"""Service for handling job-related operations."""

from typing import Any, Dict, Optional, Tuple

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
            # Get folder name prompt which extracts company and job title
            if self.prompt_service:
                folder_name_prompt = await self.prompt_service.get_folder_name_prompt()
                company_name, job_title = await self._extract_company_and_title(
                    job_description, folder_name_prompt
                )
            else:
                self.logger.warning(
                    "Prompt service not available, using fallback method"
                )
                company_name, job_title = "unknown_company", "unknown_position"

            # Return the job info dictionary
            return {
                "company_name": company_name,
                "job_title": job_title,
                "job_description": job_description,
            }
        except Exception as e:
            self.logger.error(f"Error extracting job info: {str(e)}")
            return {
                "company_name": "unknown_company",
                "job_title": "unknown_position",
                "job_description": job_description,
            }

    async def _extract_company_and_title(
        self, job_description: str, folder_name_prompt: str
    ) -> Tuple[str, str]:
        """
        Extract company name and job title using the folder name prompt.

        Args:
            job_description: The job description text
            folder_name_prompt: The folder name prompt template

        Returns:
            Tuple of (company_name, job_title)
        """
        try:
            # Use the LLM service to get the completion
            system_prompt = "You are a helpful assistant that extracts company names and job titles."

            response = await self.llm_service.get_completion(
                prompt=f"{folder_name_prompt}\n\nJob Description:\n{job_description}",
                system_prompt=system_prompt,
            )

            # Parse the response (expected format: company_name|job_title)
            if "|" in response:
                parts = response.strip().split("|")
                if len(parts) == 2:
                    company_name, job_title = parts
                    # Clean the values
                    company_name = company_name.strip().lower().replace(" ", "_")
                    job_title = job_title.strip().lower().replace(" ", "_")
                    return company_name, job_title

            # If parsing fails, return default values
            self.logger.warning(
                f"Failed to parse company/title from response: {response}"
            )
            return "unknown_company", "unknown_position"
        except Exception as e:
            self.logger.error(f"Error in _extract_company_and_title: {str(e)}")
            return "unknown_company", "unknown_position"
