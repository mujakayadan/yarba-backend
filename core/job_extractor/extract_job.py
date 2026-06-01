#!/usr/bin/env python3
"""Job description extraction module that provides an easy-to-use interface for job scraping"""

import json
import time
from pathlib import Path

from config.logging_config import get_logger
from core.models.job_extractor import JobDetails

from .extractor_manager import ExtractorManager
from .utils.html_parser import html_to_markdown

logger = get_logger(__name__)


class JobExtractor:
    """Main interface for extracting job details from URLs. This class acts as a facade
    over the ExtractorManager, providing a simplified API for end-users of the module.
    """

    def __init__(self, headless: bool = True, fast_mode: bool = True):
        """Initialize the job extractor.

        Args:
            headless: Whether to run the browser in headless mode.
            fast_mode: Whether to use faster scraping with shorter timeouts (applies to GenericExtractor).
        """
        self.manager = ExtractorManager(headless=headless, fast_mode=fast_mode)

    async def extract_from_url(self, url: str) -> JobDetails | None:
        """Extract job details from a URL.

        Args:
            url: URL of the job posting.

        Returns:
            JobDetails object with job title, description, and extraction time, or None if extraction fails.
        """
        logger.info(f"Starting job extraction for URL: {url}")
        start_time = time.time()

        try:
            result: JobDetails | None = await self.manager.extract(url)
            elapsed_time = time.time() - start_time

            if result:
                result.extraction_time = f"{elapsed_time:.2f} seconds"
                logger.info(
                    f"Successfully extracted details from {url} in {result.extraction_time}."
                )
                return result
            else:
                logger.warning(f"Extraction returned no result for {url}.")
                return None

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Error during extraction from {url} after {elapsed_time:.2f}s: {e}"
            )
            return None

    async def extract_and_save(
        self,
        url: str,
        output_path: str | Path,
        job_details_data: JobDetails | None = None,
    ) -> JobDetails | None:
        """Extract job details from a URL and save to a file.

        Args:
            url: URL of the job posting.
            output_path: Path to save the job details.
            job_details_data: Optional pre-fetched JobDetails object.

        Returns:
            JobDetails object or None if extraction fails.
        """
        job_details: JobDetails | None = None
        if job_details_data:
            job_details = job_details_data
            logger.info(
                f"Using pre-fetched job details for {url} to save to {output_path}"
            )
        else:
            job_details = await self.extract_from_url(url)

        if job_details:
            output_path_obj = Path(output_path)
            logger.info(f"Saving job details for {url} to {output_path_obj}")

            try:
                processed_description = job_details.description
                if job_details.description:
                    processed_description = html_to_markdown(job_details.description)

                if output_path_obj.suffix.lower() == ".json":
                    data_to_save = job_details.model_dump()
                    data_to_save["description"] = processed_description
                    with open(output_path_obj, "w", encoding="utf-8") as f:
                        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                else:
                    with open(output_path_obj, "w", encoding="utf-8") as f:
                        f.write("--- Job Title ---\n")
                        f.write(f"{job_details.title or 'Not available'}\n")
                        f.write("--- End of Title ---\n\n")
                        f.write("--- Job Description ---\n")
                        f.write(f"{processed_description or 'Not available'}\n")
                        f.write("--- End of Description ---\n\n")
                        f.write(
                            f"Extraction time: {job_details.extraction_time or 'N/A'}"
                        )
                logger.info(f"Job details successfully saved to {output_path_obj}")
            except OSError as e:
                logger.error(f"Failed to save job details to {output_path_obj}: {e}")
        else:
            logger.warning(
                f"No job details extracted for {url}, so nothing to save to {output_path}."
            )

        return job_details
