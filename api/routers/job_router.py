"""Router for job-related operations."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from api.dependencies.auth import require_scopes
from api.dependencies.services import get_job_service
from config.logging_config import get_logger
from core.models.job_extractor import JobDetails
from core.models.user import AuthenticatedUser
from core.services.job_service import JobService

router = APIRouter(
    tags=["jobs"],
    responses={404: {"description": "Not found"}},
)

# Initialize logger for this module
logger = get_logger(__name__)


class JobExtractionRequest(BaseModel):
    url: HttpUrl


@router.post(
    "/extract/", response_model=JobDetails, summary="Extract Job Details from URL"
)
async def extract_job_details(
    url: Annotated[
        HttpUrl, Query(description="URL of the job posting to extract details from.")
    ],
    _current_user: Annotated[
        AuthenticatedUser, Depends(require_scopes("jobs:extract"))
    ],
    job_service: JobService = Depends(get_job_service),
):
    """Extracts job title, description, and other relevant details from a given job posting URL."""
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required.")

    try:
        job_details = await job_service.extract_job_details_from_url(str(url))
        if not job_details:
            raise HTTPException(
                status_code=404,
                detail=f"Could not extract job details from the provided URL: {url}",
            )
        return job_details
    except HTTPException as http_exc:
        # Re-raise HTTPException directly
        raise http_exc
    except Exception as e:
        # Log the exception details for debugging
        logger.error(
            f"Unexpected error during job extraction from URL {url}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while processing the job extraction for URL {url}. {e}",
        )
