"""Service for handling job-related operations."""

from typing import Any, Dict, Optional

from config.logging_config import get_logger
from config.settings import settings
from core.job_extractor.extract_job import JobExtractor
from core.models.job_extractor import JobDetails
from core.schemas.job_schemas import JobInfoSchema
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService

logger = get_logger(__name__)


class JobService:
    """Service for extracting and handling job-related information."""

    def __init__(
        self,
        llm_service: LLMService,
        prompt_service: PromptService,
        job_extractor: Optional[JobExtractor] = None,
    ):
        """
        Initialize JobService.

        Args:
            llm_service: LLM service for text generation
            prompt_service: Prompt service for loading prompts
            job_extractor: Optional JobExtractor instance. If None, a default one is created.
        """
        if not prompt_service:
            raise ValueError("PromptService is required for JobService.")
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.job_extractor = job_extractor or JobExtractor()
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

    async def extract_job_details_from_url(self, url: str) -> Optional[JobDetails]:
        """
        Extract complete job details from a job posting URL.

        Args:
            url: The URL of the job posting.

        Returns:
            JobDetails object if extraction is successful, None otherwise.
        """
        self.logger.info(f"Attempting to extract job details from URL: {url}")
        try:
            job_details = await self.job_extractor.extract_from_url(url)
            if job_details:
                self.logger.info(f"Successfully extracted job details from {url}.")
            else:
                self.logger.warning(
                    f"Failed to extract job details or no details found for URL: {url}"
                )
            return job_details
        except Exception as e:
            self.logger.error(f"Error extracting job details from URL {url}: {str(e)}")
            import traceback

            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return None

    def check_job_restrictions(
        self,
        job_description: str,
        user_has_clearance_check_enabled: Optional[bool] = None,
    ) -> bool:
        """
        Check if the job description requires security clearance, US citizenship, or other restrictions.
        The check is performed if enabled globally or by user preference.

        Args:
            job_description: The job description text.
            user_has_clearance_check_enabled: User's preference to override global setting.

        Returns:
            bool: True if the job has restrictions (clearance/citizenship) and check is active, False otherwise.
        """
        perform_check: bool
        if user_has_clearance_check_enabled is not None:
            perform_check = user_has_clearance_check_enabled
            self.logger.debug(
                f"Clearance check overridden by user preference: {perform_check}"
            )
        else:
            perform_check = settings.features.enable_clearance_check
            self.logger.debug(f"Clearance check using global setting: {perform_check}")

        if not perform_check:
            self.logger.info(
                "Security clearance check is disabled. Skipping keyword search."
            )
            return False

        if not job_description or not job_description.strip():
            self.logger.warning(
                "Empty job description provided to check_security_clearance."
            )
            return False

        try:
            import re

            # Use the consolidated restriction_keywords
            keywords = settings.features.restriction_keywords

            if not keywords:
                self.logger.warning("No restriction keywords configured.")
                return False

            # Normalize job description for matching
            job_desc_lower = job_description.lower()

            # Use word boundary matching to avoid false positives
            for keyword in keywords:
                keyword_lower = keyword.lower()

                # Create a regex pattern with word boundaries for multi-word phrases
                # This prevents matching "sci" in "Computer Science" but allows "ts/sci clearance"
                if " " in keyword_lower or "/" in keyword_lower or "-" in keyword_lower:
                    # For multi-word phrases, use phrase boundary matching
                    pattern = r"\b" + re.escape(keyword_lower) + r"\b"
                else:
                    # For single words, be more strict with word boundaries
                    pattern = r"\b" + re.escape(keyword_lower) + r"\b"

                if re.search(pattern, job_desc_lower):
                    self.logger.info(
                        f"Found restriction keyword in job description: '{keyword}'"
                    )
                    return True

            self.logger.info(
                "No security clearance or citizenship keywords found in job description."
            )
            return False

        except Exception as e:
            self.logger.error(f"Error checking security clearance: {str(e)}")
            # In case of an unexpected error during the check, assume no clearance is required
            # to avoid falsely blocking users. Alternatively, could raise or return True
            # depending on desired strictness.
            return False
