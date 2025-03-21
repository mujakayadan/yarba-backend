"""Job information utilities."""

from dataclasses import dataclass
from typing import Optional, Tuple

from core.llm.base import BaseLLM

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


@dataclass
class JobInfo:
    """Data class for storing job information."""

    company_name: str
    job_title: str
    job_description: str

    @classmethod
    async def extract_from_description(
        cls,
        job_description: str,
        llm_service: BaseLLM,
    ) -> "JobInfo":
        """
        Extract job information from description using LLM.

        Args:
            job_description: Job description text
            llm_service: LLM service instance

        Returns:
            JobInfo: Extracted job information
        """
        try:
            # Extract company name and job title using LLM
            company_name, job_title = await llm_service.extract_job_info(
                job_description
            )

            return cls(
                company_name=company_name,
                job_title=job_title,
                job_description=job_description,
            )

        except Exception as e:
            logger.error(f"Failed to extract job info: {e}")
            return cls(
                company_name="Unknown Company",
                job_title="Unknown Position",
                job_description=job_description,
            )
