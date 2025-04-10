"""API router for cover letter endpoints."""

from typing import Annotated, List, Optional

from beanie import PydanticObjectId
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel

from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.user import User
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.cover_letter_service import CoverLetterService
from core.services.job_service import JobService
from core.services.profile_service import ProfileService
from utils.storage import get_storage_provider

from ..dependencies.auth import CurrentUser, get_current_active_user
from ..dependencies.services import (
    get_cover_letter_generation_service,
    get_cover_letter_service,
    get_job_service,
    get_profile_service,
)
from ..schemas.cover_letter import (
    CoverLetterCreate,
    CoverLetterResponse,
    CoverLetterUpdate,
)

logger = get_logger(__name__)

router = APIRouter()


class CoverLetterPDFResponse(BaseModel):
    """Response model for cover letter PDF URL."""

    pdf_url: Optional[str] = None


@router.get("", response_model=List[CoverLetterResponse])
async def get_cover_letters(
    current_user: CurrentUser,
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
    title: Optional[str] = Query(None, description="Filter by title (partial match)"),
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    resume_id: Optional[PydanticObjectId] = Query(
        None, description="Filter by resume ID"
    ),
) -> List[CoverLetterResponse]:
    """
    Get all cover letters for current user with optional filtering.

    Args:
        current_user: Current authenticated user
        cover_letter_service: Cover letter service
        title: Title to filter by (partial match)
        template_id: Template ID to filter by
        resume_id: Resume ID to filter by

    Returns:
        List[CoverLetterResponse]: List of cover letters
    """
    try:
        from core.repositories.cover_letter_repository import CoverLetterFilter

        # Create filter from query parameters
        filter_params = CoverLetterFilter(
            title_contains=title,
            template_id=template_id,
            resume_id=str(resume_id) if resume_id else None,
        )

        # Get filtered cover letters
        cover_letters = await cover_letter_service.filter_cover_letters(
            user_id=current_user.id,
            filter_params=filter_params,
        )

        logger.info(
            f"Retrieved {len(cover_letters)} cover letters for user {current_user.username}"
        )
        return [CoverLetterResponse.model_validate(cl) for cl in cover_letters]

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
    """
    Get a cover letter by ID.

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
        return CoverLetterResponse.model_validate(cover_letter)

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
    job_service: JobService = Depends(get_job_service),
) -> CoverLetterResponse:
    """
    Create a new cover letter.

    Args:
        cover_letter_data: Cover letter creation data
        current_user: Current authenticated user
        cover_letter_service: Cover letter service
        job_service: Job service for extracting job information

    Returns:
        CoverLetterResponse: Created cover letter
    """
    try:
        # Extract job information from job description if provided
        company_name = cover_letter_data.company_name
        job_title = cover_letter_data.job_title

        if cover_letter_data.job_description and (not company_name or not job_title):
            try:
                job_info = await job_service.extract_job_info(
                    cover_letter_data.job_description
                )
                if not company_name and "company_name" in job_info:
                    company_name = job_info["company_name"]
                if not job_title and "job_title" in job_info:
                    job_title = job_info["job_title"]
            except Exception as e:
                logger.warning(f"Error extracting job info: {str(e)}")
                # Continue even if job info extraction fails

        # Create cover letter
        cover_letter = await cover_letter_service.create_cover_letter(
            user_id=current_user.id,
            profile_id=cover_letter_data.profile_id,
            portfolio_id=cover_letter_data.portfolio_id,
            resume_id=cover_letter_data.resume_id,
            title=cover_letter_data.title,
            company_name=company_name,
            job_title=job_title,
            job_description=cover_letter_data.job_description,
            template_id=cover_letter_data.template_id,
        )

        logger.info(
            f"Created cover letter {cover_letter.id} for user {current_user.username}"
        )
        return CoverLetterResponse.model_validate(cover_letter)

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
    """
    Update a cover letter.

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
        return CoverLetterResponse.model_validate(updated_cover_letter)

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
    """
    Delete a cover letter.

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
    regenerate: bool = Query(
        False, description="Whether to regenerate even if content exists"
    ),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
    generation_service: CoverLetterGenerationService = Depends(
        get_cover_letter_generation_service
    ),
    profile_service: ProfileService = Depends(get_profile_service),
) -> CoverLetterResponse:
    """
    Generate cover letter content based on job description using user profile preferences.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        regenerate: Whether to regenerate even if content exists
        cover_letter_service: Cover letter service
        generation_service: Cover letter generation service
        profile_service: Profile service for accessing user preferences

    Returns:
        CoverLetterResponse: Updated cover letter with generated content
    """
    try:
        # Verify cover letter exists and belongs to user
        cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        # Get user profile for preferences
        llm_preferences = None
        try:
            profile = await profile_service.get_profile_by_user_id(current_user.id)
            if (
                profile
                and profile.preferences
                and hasattr(profile.preferences, "llm_preferences")
            ):
                llm_preferences = profile.preferences.llm_preferences
                logger.debug(
                    f"Using LLM preferences from user profile: {llm_preferences}"
                )
        except Exception as e:
            logger.warning(f"Error getting profile preferences: {e}")
            # Continue with default preferences

        # Generate content with preferences
        await generation_service.generate_cover_letter_content(
            cover_letter_id=cover_letter_id,
            regenerate=regenerate,
            llm_preferences=llm_preferences,
        )

        # Get updated cover letter
        updated_cover_letter = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=current_user.id,
        )

        logger.info(f"Generated cover letter content for {cover_letter_id}")
        return CoverLetterResponse.model_validate(updated_cover_letter)

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
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Return the PDF file",
        }
    },
)
async def generate_cover_letter_pdf(
    cover_letter_id: Annotated[PydanticObjectId, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    regenerate: bool = Query(
        False, description="Whether to regenerate PDF even if exists"
    ),
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
) -> Response:
    """
    Generate PDF for a cover letter.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        regenerate: Whether to regenerate PDF even if exists
        timeout: Timeout in seconds for PDF generation
        cover_letter_service: Cover letter service
        generation_service: Cover letter generation service

    Returns:
        Response: PDF content with appropriate headers
    """
    try:
        # Verify cover letter exists and belongs to user
        cover_letter = await cover_letter_service.get_cover_letter_by_id(
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
                    regenerate=regenerate,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
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

        # Return PDF with appropriate headers
        filename = f"cover_letter_{cover_letter_id}.pdf"
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_content)),
            },
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


@router.post("/{cover_letter_id}/upload-pdf", response_model=CoverLetterPDFResponse)
async def upload_cover_letter_pdf(
    cover_letter_id: PydanticObjectId = Path(..., description="Cover Letter ID"),
    file: UploadFile = File(..., description="PDF file to upload"),
    current_user: User = Depends(get_current_active_user),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
):
    """
    Upload a PDF file for a cover letter directly instead of generating it.

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
            cover_letter_id
        )

        # Check if the cover letter belongs to the user
        if cover_letter.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to upload this cover letter",
            )

        # Get storage provider
        storage_provider = get_storage_provider()

        # If cover letter already has a PDF, delete it
        if cover_letter.cover_letter_pdf_key:
            await storage_provider.delete_file(cover_letter.cover_letter_pdf_key)

        # Read the file content
        content = await file.read()

        # Save the new PDF
        pdf_key = await storage_provider.save_cover_letter_pdf(
            content, str(cover_letter_id)
        )

        # Update cover letter with the new PDF key
        cover_letter.cover_letter_pdf_key = pdf_key
        updated_cover_letter = await cover_letter_service.update_cover_letter(
            cover_letter
        )

        # Return URL for the PDF
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
    """
    Delete the PDF file for a cover letter.

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
            cover_letter_id
        )

        # Check if the cover letter belongs to the user
        if cover_letter.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this cover letter's PDF",
            )

        # Get storage provider
        storage_provider = get_storage_provider()

        # If cover letter has a PDF, delete it
        if cover_letter.cover_letter_pdf_key:
            success = await storage_provider.delete_file(
                cover_letter.cover_letter_pdf_key
            )
            if not success:
                logger.warning(
                    f"Failed to delete cover letter PDF file: {cover_letter.cover_letter_pdf_key}"
                )

            # Update cover letter to remove PDF reference
            cover_letter.cover_letter_pdf_key = None
            await cover_letter_service.update_cover_letter(cover_letter)

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
