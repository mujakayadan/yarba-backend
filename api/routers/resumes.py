"""Resumes router."""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from ...core.models.resume import Resume
from ...core.models.user import User
from ...core.services.generator import GeneratorService
from ...core.services.resume import ResumeService
from ..dependencies.services import get_generator_service, get_resume_service
from ..middleware.auth import CurrentUser
from ..schemas.resume import ResumeCreate, ResumeFilter, ResumeResponse, ResumeUpdate
from .config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    request: ResumeCreate,
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """
    Create a new resume.

    Args:
        request: Resume creation request
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        ResumeResponse: Created resume

    Raises:
        HTTPException: If resume creation fails
    """
    try:
        resume = await resume_service.create_resume(
            user_id=str(current_user.id),
            title=request.title,
            template_id=request.template_id,
        )

        logger.info(f"Resume created: {resume.id} for user {current_user.id}")
        return ResumeResponse.model_validate(resume)

    except Exception as e:
        logger.error(f"Error creating resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create resume",
        )


@router.get("", response_model=List[ResumeResponse])
async def get_resumes(
    current_user: CurrentUser,
    title: Optional[str] = Query(None, description="Filter by title"),
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    skip: int = Query(0, ge=0, description="Number of resumes to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of resumes to return"),
    resume_service: ResumeService = Depends(get_resume_service),
) -> List[ResumeResponse]:
    """
    Get all resumes for the current user.

    Args:
        current_user: Current authenticated user
        title: Optional title filter
        template_id: Optional template ID filter
        skip: Number of resumes to skip
        limit: Number of resumes to return
        resume_service: Resume service

    Returns:
        List[ResumeResponse]: List of resumes
    """
    try:
        # Create filter
        filter_params = ResumeFilter(
            title=title,
            template_id=template_id,
            skip=skip,
            limit=limit,
        )

        # Get resumes
        resumes = await resume_service.filter_resumes(
            user_id=str(current_user.id),
            filter_params=filter_params,
        )

        return [ResumeResponse.model_validate(resume) for resume in resumes]

    except Exception as e:
        logger.error(f"Error getting resumes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get resumes",
        )


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: Annotated[str, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """
    Get a resume by ID.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        ResumeResponse: Resume

    Raises:
        HTTPException: If resume not found
    """
    try:
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=str(current_user.id),
        )

        return ResumeResponse.model_validate(resume)

    except Exception as e:
        logger.error(f"Error getting resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: Annotated[str, Path(description="Resume ID")],
    request: ResumeUpdate,
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """
    Update a resume.

    Args:
        resume_id: Resume ID
        request: Resume update request
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        ResumeResponse: Updated resume

    Raises:
        HTTPException: If resume not found or update fails
    """
    try:
        # Convert request to dict
        update_data = request.model_dump(exclude_unset=True)

        # Update resume
        resume = await resume_service.update_resume(
            resume_id=resume_id,
            user_id=str(current_user.id),
            update_data=update_data,
        )

        logger.info(f"Resume updated: {resume_id}")
        return ResumeResponse.model_validate(resume)

    except Exception as e:
        logger.error(f"Error updating resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found or update failed",
        )


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: Annotated[str, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> None:
    """
    Delete a resume.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_service: Resume service

    Raises:
        HTTPException: If resume not found or deletion fails
    """
    try:
        # Delete resume
        result = await resume_service.delete_resume(
            resume_id=resume_id,
            user_id=str(current_user.id),
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found",
            )

        logger.info(f"Resume deleted: {resume_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resume",
        )


@router.post("/{resume_id}/generate", response_model=ResumeResponse)
async def generate_resume(
    resume_id: Annotated[str, Path(description="Resume ID")],
    job_description: str,
    selected_sections: dict,
    current_user: CurrentUser,
    generator_service: GeneratorService = Depends(get_generator_service),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """
    Generate resume content based on job description.

    Args:
        resume_id: Resume ID
        job_description: Job description
        selected_sections: Dictionary of section names and their generation method ('ai' or 'hardcode')
        current_user: Current authenticated user
        generator_service: Generator service
        resume_service: Resume service

    Returns:
        ResumeResponse: Updated resume with generated content

    Raises:
        HTTPException: If resume not found or generation fails
    """
    try:
        # Verify resume exists and belongs to user
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=str(current_user.id),
        )

        # Generate resume content
        updated_resume = await generator_service.generate_resume(
            user_id=str(current_user.id),
            job_description=job_description,
            selected_sections=selected_sections,
            title=resume.title,
            template_id=resume.template_id,
        )

        logger.info(f"Resume content generated: {resume_id}")
        return ResumeResponse.model_validate(updated_resume)

    except Exception as e:
        logger.error(f"Error generating resume content for {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate resume content",
        )


@router.get("/{resume_id}/pdf")
async def get_resume_pdf(
    resume_id: Annotated[str, Path(description="Resume ID")],
    current_user: CurrentUser,
    generator_service: GeneratorService = Depends(get_generator_service),
) -> bytes:
    """
    Get resume as PDF.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        generator_service: Generator service

    Returns:
        bytes: PDF content

    Raises:
        HTTPException: If resume not found or PDF generation fails
    """
    try:
        # Generate PDF
        pdf_content = await generator_service.generate_pdf(
            resume_id=resume_id,
            user_id=str(current_user.id),
        )

        logger.info(f"PDF generated for resume: {resume_id}")
        return pdf_content

    except Exception as e:
        logger.error(f"Error generating PDF for resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF",
        )
