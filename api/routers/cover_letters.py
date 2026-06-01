"""API router for cover letter endpoints."""

from datetime import datetime
from typing import Annotated

from beanie import PydanticObjectId
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.resume import LLMUsageStats
from core.models.user import User
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.cover_letter_service import CoverLetterService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.resume_service import ResumeService
from utils.storage import get_storage_provider

from ..dependencies.auth import CurrentUser, get_current_active_user
from ..dependencies.services import (
    get_cover_letter_generation_service,
    get_cover_letter_service,
    get_portfolio_service,
    get_profile_service,
    get_resume_service,
)
from ..schemas.cover_letter import (
    CoverLetterCreate,
    CoverLetterResponse,
    CoverLetterUpdate,
    PaginatedCoverLetterResponse,
)

logger = get_logger(__name__)

router = APIRouter()


class CoverLetterPDFResponse(BaseModel):
    """Response model for cover letter PDF URL."""

    pdf_url: str | None = None


class CoverLetterLLMUsageResponse(BaseModel):
    """Response model for cover letter LLM usage statistics."""

    cover_letter_id: str = Field(..., description="Cover letter ID")
    resume_id: str = Field(..., description="Resume ID")
    company_name: str | None = Field(None, description="Company name")
    job_title: str | None = Field(None, description="Job title")
    usage: LLMUsageStats = Field(..., description="LLM usage statistics")
    created_at: datetime = Field(..., description="When the cover letter was created")
    updated_at: datetime = Field(
        ..., description="When the cover letter was last updated"
    )


def convert_cover_letter_to_response(cover_letter) -> CoverLetterResponse:
    """Convert a CoverLetter model to a CoverLetterResponse schema, ensuring has_pdf is set correctly.

    Args:
        cover_letter: CoverLetter model instance

    Returns:
        CoverLetterResponse: API response model with correctly set has_pdf field
    """
    # Create a response with the data we have
    response = CoverLetterResponse.model_validate(cover_letter)

    # Explicitly set has_pdf based on cover_letter_pdf_key
    response.has_pdf = bool(cover_letter.cover_letter_pdf_key)

    return response


@router.get("", response_model=PaginatedCoverLetterResponse)
async def get_cover_letters(
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
    template_id: str | None = Query(None, description="Filter by template ID"),
    resume_id: PydanticObjectId | None = Query(None, description="Filter by resume ID"),
    skip: int = Query(0, ge=0, description="Number of cover letters to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of cover letters to return"
    ),
    sort_by: str = Query("updated_desc", description="Sort field and direction"),
) -> PaginatedCoverLetterResponse:
    """Get all cover letters for current user with optional filtering, pagination and sorting.

    Args:
        current_user: Current authenticated user
        cover_letter_service: Cover letter service
        template_id: Template ID to filter by
        resume_id: Resume ID to filter by
        skip: Number of cover letters to skip
        limit: Number of cover letters to return
        sort_by: Sort field and direction

    Returns:
        PaginatedCoverLetterResponse: Paginated list of cover letters
    """
    try:
        # Create filter
        from api.schemas import CoverLetterFilter

        filter_params = CoverLetterFilter(
            template_id=template_id,
            resume_id=resume_id,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
        )

        # Get cover letters matching filter
        cover_letters = await cover_letter_service.filter_cover_letters(
            user_id=current_user.id,
            filter_params=filter_params,
        )

        # Count total matching filter (without pagination)
        total = await cover_letter_service.count_cover_letters(
            user_id=current_user.id,
            filter_params=filter_params,
        )

        logger.info(
            f"Retrieved {len(cover_letters)} cover letters for user {current_user.username}, total: {total}"
        )

        # Convert to response format
        cover_letter_responses = [
            convert_cover_letter_to_response(cl) for cl in cover_letters
        ]

        return PaginatedCoverLetterResponse(
            items=cover_letter_responses,
            total=total,
        )

    except Exception as e:
        logger.error(f"Error retrieving cover letters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cover letters",
        )


@router.get("/{cover_letter_id}", response_model=CoverLetterResponse)
async def get_cover_letter(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
) -> CoverLetterResponse:
    """Get a cover letter by ID.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        cover_letter_service: Cover letter service

    Returns:
        CoverLetterResponse: Cover letter data
    """
    try:
        cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        logger.info(
            f"Retrieved cover letter {cover_letter_id} for user {current_user.username}"
        )
        return convert_cover_letter_to_response(cover_letter)

    except Exception as e:
        logger.error(f"Error retrieving cover letter {cover_letter_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )


@router.post(
    "", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED
)
async def create_cover_letter(
    cover_letter_data: Annotated[
        CoverLetterCreate, Body(description="Cover letter data")
    ],
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
    resume_service: ResumeService = Depends(get_resume_service),
    profile_service: ProfileService = Depends(get_profile_service),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    generation_service: CoverLetterGenerationService = Depends(
        get_cover_letter_generation_service
    ),
) -> CoverLetterResponse:
    """Create a new cover letter based on an existing resume.

    Args:
        cover_letter_data: Cover letter creation data containing:
            - resume_id: Resume ID that this cover letter is based on
            - generate_pdf: Optional boolean to trigger immediate PDF generation (default: False)
        current_user: Current authenticated user
        cover_letter_service: Cover letter service
        resume_service: Resume service for getting resume details
        profile_service: Profile service for accessing user preferences
        portfolio_service: Portfolio service for getting active portfolio
        generation_service: Cover letter generation service for PDF generation

    Returns:
        CoverLetterResponse: Created cover letter with has_pdf=True if PDF was generated

    Raises:
        HTTPException: If cover letter creation fails
    """
    try:
        # Get user ID
        user_id = PydanticObjectId(current_user.id)

        # Get user profile
        try:
            profile = await profile_service.get_profile_by_user_id(user_id)
            if not profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No profile found. Please create a profile first.",
                )
        except Exception as e:
            logger.error(f"Error retrieving profile: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user profile.",
            )

        # Get user portfolio
        try:
            portfolio = await portfolio_service.get_portfolio_by_user_id(user_id)
            if not portfolio:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No portfolio found. Please create a portfolio first.",
                )
        except Exception as e:
            logger.error(f"Error retrieving portfolio: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user portfolio.",
            )

        # Get default template from profile or use default
        template_id = "default"
        if profile.system_preferences and profile.system_preferences.templates:
            template_id = profile.system_preferences.templates.get(
                "default_cover_letter_template_id", "default"
            )

        # Create cover letter
        cover_letter = await cover_letter_service.create_cover_letter(
            user_id=user_id,
            profile_id=profile.id,
            portfolio_id=portfolio.id,
            resume_id=cover_letter_data.resume_id,
            template_id=template_id,
        )

        logger.info(
            f"Created cover letter {cover_letter.id} for user {current_user.username}"
        )

        try:
            # Always generate cover letter content first
            logger.info(f"Generating content for cover letter: {cover_letter.id}")
            await generation_service.generate_cover_letter_content(
                cover_letter_id=cover_letter.id
            )

            # Fetch the updated cover letter with content before proceeding
            cover_letter = await cover_letter_service.get_cover_letter_by_id(
                cover_letter_id=cover_letter.id,
                user_id=user_id,
            )

            # Verify content was generated successfully
            if not cover_letter.content:
                logger.error(
                    f"Content generation failed for cover letter: {cover_letter.id}"
                )
                raise Exception("Failed to generate cover letter content")

            logger.info(
                f"Successfully generated content for cover letter: {cover_letter.id}"
            )

            # If PDF generation is requested, generate PDF
            if cover_letter_data.generate_pdf:
                logger.info(f"Generating PDF for cover letter: {cover_letter.id}")
                await generation_service.generate_pdf(cover_letter.id)

                # Get the updated cover letter with PDF information
                cover_letter = await cover_letter_service.get_cover_letter_by_id(
                    cover_letter_id=cover_letter.id,
                    user_id=user_id,
                )

            logger.info(f"Cover letter generation completed for: {cover_letter.id}")
        except Exception as generation_error:
            # Log error but don't fail the entire cover letter creation
            logger.error(
                f"Error during cover letter generation: {str(generation_error)}"
            )
            # We'll still return the created cover letter without content or PDF

        return convert_cover_letter_to_response(cover_letter)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error creating cover letter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cover letter",
        )


@router.patch("/{cover_letter_id}", response_model=CoverLetterResponse)
async def update_cover_letter(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover letter ID")],
    cover_letter_data: Annotated[
        CoverLetterUpdate, Body(description="Cover letter update data")
    ],
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
) -> CoverLetterResponse:
    """Update a cover letter.

    Args:
        cover_letter_id: Cover letter ID
        cover_letter_data: Cover letter update data
        current_user: Current authenticated user
        cover_letter_service: Cover letter service

    Returns:
        CoverLetterResponse: Updated cover letter
    """
    try:
        # Get raw data from Pydantic model
        update_data = cover_letter_data.model_dump(exclude_unset=True)

        # Update cover letter
        updated_cover_letter = await cover_letter_service.update_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
            **update_data,
        )

        logger.info(
            f"Updated cover letter {cover_letter_id} for user {current_user.username}"
        )
        return convert_cover_letter_to_response(updated_cover_letter)

    except Exception as e:
        logger.error(f"Error updating cover letter {cover_letter_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cover_letter(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
) -> None:
    """Delete a cover letter.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        cover_letter_service: Cover letter service
    """
    try:
        await cover_letter_service.delete_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        logger.info(
            f"Deleted cover letter {cover_letter_id} for user {current_user.username}"
        )

    except Exception as e:
        logger.error(f"Error deleting cover letter {cover_letter_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )


@router.post("/{cover_letter_id}/generate", response_model=CoverLetterResponse)
async def generate_cover_letter(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
    generation_service: CoverLetterGenerationService = Depends(
        get_cover_letter_generation_service
    ),
) -> CoverLetterResponse:
    """Generate cover letter content based on job description.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        cover_letter_service: Cover letter service
        generation_service: Cover letter generation service

    Returns:
        CoverLetterResponse: Updated cover letter with generated content
    """
    try:
        # Verify cover letter exists and belongs to user
        await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        # Generate content
        await generation_service.generate_cover_letter_content(
            cover_letter_id=cover_letter_id
        )

        # Get updated cover letter
        updated_cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        logger.info(f"Generated cover letter content for {cover_letter_id}")
        return convert_cover_letter_to_response(updated_cover_letter)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating cover letter content for {cover_letter_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cover letter content",
        )


@router.post(
    "/{cover_letter_id}/pdf",
    response_model=CoverLetterPDFResponse,
)
async def generate_cover_letter_pdf(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    timeout: int = Query(
        30,
        description="Timeout in seconds for PDF generation",
        ge=5,  # Minimum 5 seconds
        le=60,  # Maximum 60 seconds
    ),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
    generation_service: CoverLetterGenerationService = Depends(
        get_cover_letter_generation_service
    ),
) -> CoverLetterPDFResponse:
    """Generate PDF for a cover letter and return its URL.

    NOTE: This endpoint returns a URL to the PDF file stored in S3, not the PDF content itself.
    Clients should use the returned URL to download or display the PDF.

    The PDF will be generated and stored in S3 before returning the URL.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        timeout: Timeout in seconds for PDF generation
        cover_letter_service: Cover letter service
        generation_service: Cover letter generation service

    Returns:
        CoverLetterPDFResponse: Object containing the PDF URL
    """
    try:
        # Verify cover letter exists and belongs to user
        await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        # Generate PDF with timeout
        import asyncio

        try:
            logger.info(
                f"Starting PDF generation for cover letter: {cover_letter_id} with timeout {timeout}s"
            )
            pdf_content = await asyncio.wait_for(
                generation_service.generate_pdf(
                    cover_letter_id=cover_letter_id,
                ),
                timeout=timeout,
            )
        except TimeoutError:
            logger.error(
                f"PDF generation timed out after {timeout} seconds for cover letter: {cover_letter_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="PDF generation timed out. Please try again later.",
            )

        logger.info(
            f"Generated PDF for cover letter {cover_letter_id}, size: {len(pdf_content)} bytes"
        )

        # Get the updated cover letter to retrieve the S3 key
        updated_cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        # Get the PDF URL from S3
        if updated_cover_letter.cover_letter_pdf_key:
            storage_provider = get_storage_provider()
            pdf_url = storage_provider.get_url(
                updated_cover_letter.cover_letter_pdf_key
            )
            return CoverLetterPDFResponse(pdf_url=pdf_url)
        else:
            # This should never happen, but just in case
            logger.error(
                f"PDF was generated but S3 key is missing for cover letter {cover_letter_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF was generated but storage key is missing",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating PDF for cover letter {cover_letter_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF",
        )


@router.get(
    "/{cover_letter_id}/pdf",
    response_model=CoverLetterPDFResponse,
    responses={
        200: {"description": "PDF URL"},
        404: {"description": "Cover letter not found or PDF not available"},
    },
)
async def get_cover_letter_pdf(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
) -> CoverLetterPDFResponse:
    """Get the URL for a cover letter PDF.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        cover_letter_service: Cover letter service

    Returns:
        CoverLetterPDFResponse: Object containing the PDF URL

    Raises:
        HTTPException: If cover letter not found or PDF not available
    """
    try:
        # Verify cover letter exists and belongs to user
        cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        # Check if PDF exists
        if not cover_letter.cover_letter_pdf_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF not available for this cover letter. Generate PDF first.",
            )

        # Get the PDF URL from S3
        storage_provider = get_storage_provider()
        pdf_url = storage_provider.get_url(cover_letter.cover_letter_pdf_key)

        logger.info(f"Retrieved PDF URL for cover letter {cover_letter_id}")
        return CoverLetterPDFResponse(pdf_url=pdf_url)

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving cover letter PDF URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PDF URL",
        )


@router.post("/{cover_letter_id}/upload-pdf", response_model=CoverLetterPDFResponse)
async def upload_cover_letter_pdf(
    cover_letter_id: PydanticObjectId = Path(..., description="Cover Letter ID"),
    file: UploadFile = File(..., description="PDF file to upload"),
    current_user: User = Depends(get_current_active_user),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
):
    """Upload a PDF file for a cover letter directly instead of generating it.

    Args:
        cover_letter_id: Cover Letter ID
        file: PDF file to upload
        current_user: Current authenticated user
        cover_letter_service: Cover Letter service

    Returns:
        PDF URL
    """
    # Check file content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    try:
        # Get the cover letter
        cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        # Read the file content
        content = await file.read()

        # Get storage provider
        storage_provider = get_storage_provider()

        # If cover letter already has a PDF in S3, delete it
        if cover_letter.cover_letter_pdf_key:
            try:
                await storage_provider.delete_file(cover_letter.cover_letter_pdf_key)
                logger.info(
                    f"Deleted previous PDF from S3: {cover_letter.cover_letter_pdf_key}"
                )
            except Exception as delete_error:
                logger.error(f"Error deleting previous PDF: {str(delete_error)}")

        # Save the new PDF to S3
        pdf_key = await storage_provider.save_cover_letter_pdf(
            content, str(cover_letter_id)
        )
        logger.info(f"Saved new cover letter PDF to S3: {pdf_key}")

        # Update cover letter with the new PDF key
        await cover_letter_service.update_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
            update_data={"cover_letter_pdf_key": pdf_key},
        )

        # Get the URL for the PDF
        pdf_url = storage_provider.get_url(pdf_key)
        return {"pdf_url": pdf_url}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )
    except Exception as e:
        logger.error(f"Error uploading cover letter PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload cover letter PDF: {str(e)}",
        )


@router.delete("/{cover_letter_id}/pdf", response_model=CoverLetterPDFResponse)
async def delete_cover_letter_pdf(
    cover_letter_id: PydanticObjectId = Path(..., description="Cover Letter ID"),
    current_user: User = Depends(get_current_active_user),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
):
    """Delete the PDF file for a cover letter.

    Args:
        cover_letter_id: Cover Letter ID
        current_user: Current authenticated user
        cover_letter_service: Cover Letter service

    Returns:
        Empty PDF URL
    """
    try:
        # Get the cover letter
        cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        # Get storage provider
        storage_provider = get_storage_provider()

        # If cover letter has a PDF in S3, delete it
        if cover_letter.cover_letter_pdf_key:
            try:
                success = await storage_provider.delete_file(
                    cover_letter.cover_letter_pdf_key
                )
                if success:
                    logger.info(
                        f"Deleted PDF from S3: {cover_letter.cover_letter_pdf_key}"
                    )
                else:
                    logger.warning(
                        f"Failed to delete PDF from S3: {cover_letter.cover_letter_pdf_key}"
                    )
            except Exception as e:
                logger.error(f"Error deleting PDF from S3: {str(e)}")

            # Update cover letter to remove PDF key
            await cover_letter_service.update_cover_letter(
                cover_letter_id=cover_letter_id,
                user_id=current_user.id,
                update_data={"cover_letter_pdf_key": None},
            )

        return {"pdf_url": None}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )
    except Exception as e:
        logger.error(f"Error deleting cover letter PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cover letter PDF: {str(e)}",
        )


@router.get("/{cover_letter_id}/llm-usage", response_model=CoverLetterLLMUsageResponse)
async def get_cover_letter_llm_usage(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover Letter ID")],
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
    resume_service: ResumeService = Depends(get_resume_service),
) -> CoverLetterLLMUsageResponse:
    """Get LLM usage statistics for a specific cover letter.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        cover_letter_service: Cover letter service
        resume_service: Resume service

    Returns:
        Cover letter LLM usage statistics

    Raises:
        HTTPException: If cover letter is not found or access is denied
    """
    try:
        # Get cover letter with usage statistics
        cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=PydanticObjectId(current_user.id),
        )

        # Get associated resume data for company name and job title
        company_name = None
        job_title = None
        if cover_letter.resume_id:
            try:
                resume = await resume_service.get_resume_by_id(
                    resume_id=cover_letter.resume_id,
                    user_id=PydanticObjectId(current_user.id),
                )
                company_name = resume.company_name
                job_title = resume.job_title
            except Exception:
                # Just continue without resume details if we can't get them
                pass

        # Return usage data along with basic cover letter info
        return {
            "cover_letter_id": str(cover_letter.id),
            "resume_id": str(cover_letter.resume_id),
            "company_name": company_name,
            "job_title": job_title,
            "usage": cover_letter.llm_usage,
            "created_at": cover_letter.created_at,
            "updated_at": cover_letter.updated_at,
        }

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )
    except Exception as e:
        logger.error(f"Error retrieving cover letter LLM usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cover letter LLM usage: {str(e)}",
        )
