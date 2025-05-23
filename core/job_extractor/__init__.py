"""
YARBA Job Crawler - A simple job description extractor
"""

from core.models.job_extractor import JobDetails

from .extract_job import JobExtractor

__all__ = [
    "JobExtractor",
    "JobDetails",
]
