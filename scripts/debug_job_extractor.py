#!/usr/bin/env python
"""Debug script to directly test the job extractor without going through the API."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Changed to INFO for less verbose output, can be DEBUG if needed
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Set up Windows asyncio policy
if sys.platform == "win32":
    print("Setting WindowsProactorEventLoopPolicy for asyncio.")
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from core.job_extractor.extract_job import JobExtractor


async def debug_extraction():
    # Set headless=False to see what's happening in the browser
    job_extractor = JobExtractor(headless=False, fast_mode=True)

    # Test with LinkedIn URL
    linkedin_url = "https://www.linkedin.com/jobs/view/4231948770/?refId=Zr0wg3bpSKSpMxzgDuMmWw%3D%3D&trackingId=h1tHDf%2F0Ti6pQvcqRdhf%2BQ%3D%3D"
    print(f"\nTesting LinkedIn URL: {linkedin_url}")
    linkedin_result = await job_extractor.extract_from_url(linkedin_url)

    print("\nLinkedIn Result:")
    if linkedin_result:
        print(f"Description: {linkedin_result.description}")
        print(
            f"Description length: {len(linkedin_result.description) if linkedin_result.description else 0}"
        )
        print(f"Extraction time: {linkedin_result.extraction_time}")
    else:
        print("Failed to extract LinkedIn job details")

    # # Test with generic URL (Lensa)
    # generic_url = "https://lensa.com/job-application-research-engineer-robotics-in-menlo-park-ca/cpc-jd-v3/f40c37113c34be30f481f63a0790ac47a617ead3fcbe18099b77c7b176a8d673?tr=8640330297e84040b4231e679cddd699incc1&utm_source=linkedin&utm_medium=slot&utm_campaign=Engineers&utm_term=jse"
    # print(f"\nTesting Generic URL: {generic_url}")
    # generic_result = await job_extractor.extract_from_url(generic_url)

    # print("\nGeneric URL Result:")
    # if generic_result:
    #     print(f"Title: {generic_result.title}")
    #     print(f"Description length: {len(generic_result.description) if generic_result.description else 0}")
    #     print(f"Extraction time: {generic_result.extraction_time}")
    # else:
    #     print("Failed to extract generic job details")


if __name__ == "__main__":
    asyncio.run(debug_extraction())
