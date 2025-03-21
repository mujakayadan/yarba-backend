"""Service for handling job-related operations."""

from typing import Any, Dict, Optional

from config.logging_config import get_logger
from core.services.llm_service import LLMService

logger = get_logger(__name__)


class JobService:
    """Service for extracting and handling job-related information."""

    def __init__(self, llm_service: LLMService):
        """
        Initialize JobService.

        Args:
            llm_service: LLM service for text generation
        """
        self.llm_service = llm_service
        self.logger = logger

    async def extract_job_info(self, job_description: str) -> Dict[str, Any]:
        """
        Extract information from a job description.

        Args:
            job_description: The job description text

        Returns:
            Dictionary containing extracted job information
        """
        try:
            system_prompt = """You are an AI assistant that extracts key information from job descriptions.
Your task is to extract the company name, job title, and other relevant details from the provided job description.
Provide your response as JSON with the following fields:
- company_name: The name of the company
- job_title: The title of the position
- required_skills: A list of skills required for the position
- preferred_skills: A list of preferred or nice-to-have skills
- job_level: The experience level (entry, mid, senior, etc.)
- job_type: The type of employment (full-time, part-time, contract, etc.)
If any field cannot be determined, use null for that field."""

            user_prompt = f"""Please extract the key information from the following job description:

{job_description}

Return the information in JSON format."""

            # Get completion from LLM
            response = await self.llm_service.get_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                response_format={"type": "json_object"},
            )

            # Parse the JSON response
            import json

            try:
                job_info = json.loads(response)

                # Ensure required fields are present
                job_info["company_name"] = (
                    job_info.get("company_name") or "Unknown Company"
                )
                job_info["job_title"] = job_info.get("job_title") or "Unknown Position"
                job_info["job_description"] = job_description

                return job_info
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse LLM response as JSON: {response}")
                return {
                    "company_name": "Unknown Company",
                    "job_title": "Unknown Position",
                    "job_description": job_description,
                }

        except Exception as e:
            self.logger.error(f"Error extracting job info: {str(e)}")
            return {
                "company_name": "Unknown Company",
                "job_title": "Unknown Position",
                "job_description": job_description,
            }
