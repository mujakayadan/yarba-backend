"""Service for handling job-related operations."""

from typing import Any, Dict

from config.constants import APP_CONSTANTS
from config.logging_config import get_logger
from core.schemas.job_schemas import JobInfoSchema
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService

logger = get_logger(__name__)


class JobService:
    """Service for extracting and handling job-related information."""

    def __init__(self, llm_service: LLMService, prompt_service: PromptService):
        """
        Initialize JobService.

        Args:
            llm_service: LLM service for text generation
            prompt_service: Prompt service for loading prompts
        """
        if not prompt_service:
            raise ValueError("PromptService is required for JobService.")
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.logger = logger

    async def extract_job_info(self, job_description: str) -> Dict[str, Any]:
        """
        Extract basic information from a job description using LLM.

        Args:
            job_description: The job description text

        Returns:
            Dictionary containing extracted job information (company_name, job_title)
            or default values if extraction fails.
        """
        default_result = {
            "company_name": "unknown_company",
            "job_title": "unknown_position",
        }

        if not job_description or not job_description.strip():
            self.logger.warning("Empty job description provided, returning defaults.")
            return default_result

        extracted_info = default_result  # Initialize with default
        try:
            # 1. Format the folder_name prompt
            self.logger.debug("Formatting folder_name prompt.")
            variables = {"job_description": job_description}
            folder_prompt = await self.prompt_service.format_prompt(
                "folder_name", variables
            )

            # 2. Call LLM for structured output
            self.logger.info("Calling LLM to extract company name and job title.")
            tags = ["operation:extract_job_info"]
            # Assuming LLMService is configured for the correct user elsewhere or is generic

            # LLMService.get_structured_completion now returns a tuple:
            # (parsed_schema_object, litellm_model_response_object)
            parsed_job_info_schema, _ = (
                await self.llm_service.get_structured_completion(
                    prompt=folder_prompt,
                    schema_model=JobInfoSchema,
                    # system_prompt=None, # Optional: Add specific system prompt if needed
                    tags=tags,
                    fallback_to_text=False,  # We strictly need the JSON structure
                )
            )

            if parsed_job_info_schema and isinstance(
                parsed_job_info_schema, JobInfoSchema
            ):
                extracted_info = parsed_job_info_schema.model_dump()
                # Optional: Add validation for default values if needed, though the prompt requests fallbacks
                if not extracted_info.get("company_name"):
                    extracted_info["company_name"] = default_result["company_name"]
                if not extracted_info.get("job_title"):
                    extracted_info["job_title"] = default_result["job_title"]
            else:
                self.logger.error(
                    "LLM did not return a valid JobInfoSchema object for job info extraction."
                )
                # Keep extracted_info as default_result

            self.logger.info(
                f"Extracted job info - company: {extracted_info['company_name']}, title: {extracted_info['job_title']}"
            )
            return extracted_info  # Return the result (either extracted or default)

        except Exception as e:
            self.logger.error(f"Error extracting job info via LLM: {str(e)}")
            import traceback

            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return default_result

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
