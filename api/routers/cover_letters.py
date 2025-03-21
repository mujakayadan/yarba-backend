"""Cover letters router."""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from config import get_logger
from core.models.resume import Resume
from core.models.user import User
from core.services.generator_service import GeneratorService
from core.services.resume_service import ResumeService

from ..dependencies.services import get_generator_service, get_resume_service
from ..middleware.auth import CurrentUser
from ..schemas import CoverLetterCreate, CoverLetterResponse, ResumeFilter, ResumeUpdate

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED
)
async def create_cover_letter(
    request: CoverLetterCreate,
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> CoverLetterResponse:
    """
    Create a new cover letter.

    Args:
        request: Cover letter creation request
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        CoverLetterResponse: Created cover letter

    Raises:
        HTTPException: If cover letter creation fails
    """
    try:
        # Create a resume with is_cover_letter=True
        resume = await resume_service.create_resume(
            user_id=str(current_user.id),
            title=request.title,
            template_id=request.template_id,
            is_cover_letter=True,
        )

        logger.info(f"Cover letter created: {resume.id} for user {current_user.id}")
        return CoverLetterResponse.model_validate(resume)

    except Exception as e:
        logger.error(f"Error creating cover letter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cover letter",
        )


@router.get("", response_model=List[CoverLetterResponse])
async def get_cover_letters(
    current_user: CurrentUser,
    title: Optional[str] = Query(None, description="Filter by title"),
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    skip: int = Query(0, ge=0, description="Number of cover letters to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Number of cover letters to return"
    ),
    resume_service: ResumeService = Depends(get_resume_service),
) -> List[CoverLetterResponse]:
    """
    Get all cover letters for the current user.

    Args:
        current_user: Current authenticated user
        title: Optional title filter
        template_id: Optional template ID filter
        skip: Number of cover letters to skip
        limit: Number of cover letters to return
        resume_service: Resume service

    Returns:
        List[CoverLetterResponse]: List of cover letters
    """
    try:
        # Create filter
        filter_params = ResumeFilter(
            title=title,
            template_id=template_id,
            skip=skip,
            limit=limit,
            is_cover_letter=True,
        )

        # Get cover letters
        resumes = await resume_service.filter_resumes(
            user_id=str(current_user.id),
            filter_params=filter_params,
        )

        return [CoverLetterResponse.model_validate(resume) for resume in resumes]

    except Exception as e:
        logger.error(f"Error getting cover letters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cover letters",
        )


@router.get("/{cover_letter_id}", response_model=CoverLetterResponse)
async def get_cover_letter(
    cover_letter_id: Annotated[str, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> CoverLetterResponse:
    """
    Get a cover letter by ID.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        CoverLetterResponse: Cover letter

    Raises:
        HTTPException: If cover letter not found
    """
    try:
        resume = await resume_service.get_resume_by_id(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
        )

        if not resume.is_cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found",
            )

        return CoverLetterResponse.model_validate(resume)

    except Exception as e:
        logger.error(f"Error getting cover letter {cover_letter_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found",
        )


@router.put("/{cover_letter_id}", response_model=CoverLetterResponse)
async def update_cover_letter(
    cover_letter_id: Annotated[str, Path(description="Cover letter ID")],
    request: ResumeUpdate,
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> CoverLetterResponse:
    """
    Update a cover letter.

    Args:
        cover_letter_id: Cover letter ID
        request: Cover letter update request
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        CoverLetterResponse: Updated cover letter

    Raises:
        HTTPException: If cover letter not found or update fails
    """
    try:
        # Verify it's a cover letter
        resume = await resume_service.get_resume_by_id(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
        )

        if not resume.is_cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found",
            )

        # Convert request to dict
        update_data = request.model_dump(exclude_unset=True)

        # Update cover letter
        updated_resume = await resume_service.update_resume(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
            update_data=update_data,
        )

        logger.info(f"Cover letter updated: {cover_letter_id}")
        return CoverLetterResponse.model_validate(updated_resume)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cover letter {cover_letter_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found or update failed",
        )


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cover_letter(
    cover_letter_id: Annotated[str, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> None:
    """
    Delete a cover letter.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        resume_service: Resume service

    Raises:
        HTTPException: If cover letter not found or deletion fails
    """
    try:
        # Verify it's a cover letter
        resume = await resume_service.get_resume_by_id(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
        )

        if not resume.is_cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found",
            )

        # Delete cover letter
        result = await resume_service.delete_resume(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found",
            )

        logger.info(f"Cover letter deleted: {cover_letter_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cover letter {cover_letter_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cover letter",
        )


@router.post("/{cover_letter_id}/generate", response_model=CoverLetterResponse)
async def generate_cover_letter(
    cover_letter_id: Annotated[str, Path(description="Cover letter ID")],
    job_description: str,
    current_user: CurrentUser,
    generator_service: GeneratorService = Depends(get_generator_service),
    resume_service: ResumeService = Depends(get_resume_service),
) -> CoverLetterResponse:
    """
    Generate cover letter content based on job description.

    Args:
        cover_letter_id: Cover letter ID
        job_description: Job description
        current_user: Current authenticated user
        generator_service: Generator service
        resume_service: Resume service

    Returns:
        CoverLetterResponse: Updated cover letter with generated content

    Raises:
        HTTPException: If cover letter not found or generation fails
    """
    try:
        # Verify it's a cover letter
        resume = await resume_service.get_resume_by_id(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
        )

        if not resume.is_cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found",
            )

        # Generate cover letter content
        updated_resume = await generator_service.generate_cover_letter(
            user_id=str(current_user.id),
            job_description=job_description,
            title=resume.title,
            template_id=resume.template_id,
            resume_id=cover_letter_id,
        )

        logger.info(f"Cover letter content generated: {cover_letter_id}")
        return CoverLetterResponse.model_validate(updated_resume)

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


@router.get("/{cover_letter_id}/pdf")
async def get_cover_letter_pdf(
    cover_letter_id: Annotated[str, Path(description="Cover letter ID")],
    current_user: CurrentUser,
    generator_service: GeneratorService = Depends(get_generator_service),
    resume_service: ResumeService = Depends(get_resume_service),
) -> bytes:
    """
    Get cover letter as PDF.

    Args:
        cover_letter_id: Cover letter ID
        current_user: Current authenticated user
        generator_service: Generator service
        resume_service: Resume service

    Returns:
        bytes: PDF content

    Raises:
        HTTPException: If cover letter not found or PDF generation fails
    """
    try:
        # Verify it's a cover letter
        resume = await resume_service.get_resume_by_id(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
        )

        if not resume.is_cover_letter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cover letter not found",
            )

        # Generate PDF
        pdf_content = await generator_service.generate_pdf(
            resume_id=cover_letter_id,
            user_id=str(current_user.id),
        )

        logger.info(f"PDF generated for cover letter: {cover_letter_id}")
        return pdf_content

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
