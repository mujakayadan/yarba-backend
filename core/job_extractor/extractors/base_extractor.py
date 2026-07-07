from abc import ABC, abstractmethod

import config.logging_config as logging_config
from core.models.job_extractor import JobDetails

logger = logging_config.get_logger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for all job extractors."""

    def __init__(self, headless: bool = True, **kwargs):
        """Initialize the base extractor.

        Args:
            headless: Whether to run the browser in headless mode.
            **kwargs: Additional arguments that specific extractors might need (e.g., fast_mode).
        """
        self.headless = headless
        # Store any other arguments for subclasses
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    async def scrape_job_posting(self, job_url: str) -> JobDetails | None:
        """Extract job details from a job posting URL.
        This method must be implemented by all subclasses.

        Args:
            job_url: URL of the job posting.

        Returns:
            A JobDetails Pydantic model instance containing the extracted data, or None if extraction fails.
        """

    async def init_playwright(self):
        """Initialize Playwright."""
        try:
            from playwright.async_api import async_playwright

            return await async_playwright().start()
        except Exception as e:
            # Log the original exception with traceback for more details
            logger.error(f"Failed to initialize Playwright: {e}", exc_info=True)
            raise
