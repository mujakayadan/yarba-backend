"""Resumes router."""

from typing import Annotated, List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from api.dependencies.services import (
    get_job_service,
    get_portfolio_service,
    get_profile_service,
    get_resume_generation_service,
    get_resume_service,
)
from api.middleware.auth import CurrentUser
from api.schemas import ResumeCreate, ResumeFilter, ResumeResponse, ResumeUpdate
from config import get_logger
from config.settings import settings
from core.exceptions.base import NotFoundException
from core.models.portfolio import Portfolio
from core.services.job_service import JobService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    request: ResumeCreate,
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
    job_service: JobService = Depends(get_job_service),
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
    profile_service: ProfileService = Depends(get_profile_service),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
) -> ResumeResponse:
    """
    Create a new resume.

    Args:
        request: Resume creation request
        current_user: Current authenticated user
        resume_service: Resume service
        job_service: Job service
        resume_generation_service: Resume generation service
        profile_service: Profile service
        portfolio_service: Portfolio service

    Returns:
        ResumeResponse: Created resume

    Raises:
        HTTPException: If resume creation fails
    """
    try:
        # Create basic resume with title and template
        # First, try to get the user's profile
        try:
            profile = await profile_service.get_profile_by_user_id(current_user.id)
            profile_id = profile.id
        except Exception as e:
            logger.warning(
                f"Error getting profile for user {current_user.id}: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User profile not found. Please create a profile first.",
            )

        # Get the user's portfolio or create one if it doesn't exist
        try:
            # Try to get an existing portfolio
            portfolio = await portfolio_service.get_portfolio_by_user_id(
                current_user.id
            )
            portfolio_id = portfolio.id
        except NotFoundException:
            # Create a default portfolio if none exists
            logger.info(
                f"No portfolio found for user {current_user.id}, creating a default one"
            )
            portfolio_repository = portfolio_service.portfolio_repository
            portfolio = await portfolio_repository.create_for_user(
                user_id=PydanticObjectId(current_user.id), profile_id=profile_id
            )
            portfolio_id = portfolio.id

        # Create the resume with the profile ID and other fields
        try:
            resume = await resume_service.create_resume(
                user_id=PydanticObjectId(current_user.id),
                profile_id=profile_id,
                portfolio_id=portfolio_id,
                job_description=getattr(request, "job_description", None),
            )
        except NotFoundException as e:
            if "portfolio" in str(e).lower():
                # Specific error message for missing portfolio
                logger.warning(f"Portfolio not found for user {current_user.id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User portfolio not found. Please create a portfolio first.",
                )
            # Re-raise other NotFoundException errors
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # If job description is provided, use it to enhance the resume
        if request.job_description:
            # Extract job info
            job_info = await job_service.extract_job_info(request.job_description)

            # Update resume with job information
            resume = await resume_service.update_resume(
                resume_id=resume.id,
                user_id=PydanticObjectId(current_user.id),
                update_data={
                    "job_description": request.job_description,
                    "company_name": job_info.get("company_name"),
                    "job_title": job_info.get("job_title"),
                },
            )

            # Get user's profile for preferences
            try:
                profile = await profile_service.get_profile_by_user_id(current_user.id)

                # Get selected sections from request or profile
                regenerate_sections = request.selected_sections
                if not regenerate_sections and profile and profile.preferences:
                    if hasattr(profile.preferences, "section_preferences"):
                        regenerate_sections = profile.preferences.section_preferences
                    else:
                        regenerate_sections = settings.preferences.section_preferences
                elif not regenerate_sections:
                    regenerate_sections = settings.preferences.section_preferences

                # Generate resume content based on job description
                if regenerate_sections:
                    await resume_generation_service.generate_resume_content(
                        resume_id=resume.id,
                        regenerate_sections=list(regenerate_sections),
                    )
                    # Fetch the updated resume
                    resume = await resume_service.get_resume_by_id(
                        resume_id=resume.id, user_id=PydanticObjectId(current_user.id)
                    )
            except Exception as profile_error:
                logger.warning(
                    f"Error getting profile or generating content: {str(profile_error)}"
                )
                # Continue without generating content to avoid blocking resume creation

        logger.info(f"Resume created: {resume.id} for user {current_user.id}")
        return ResumeResponse.model_validate(resume)

    except Exception as e:
        logger.error(f"Error creating resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resume: {str(e)}",
        )


@router.get("", response_model=List[ResumeResponse])
async def get_resumes(
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of resumes to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of resumes to return"),
    resume_service: ResumeService = Depends(get_resume_service),
) -> List[ResumeResponse]:
    """
    Get all resumes for the current user.

    Args:
        current_user: Current authenticated user
        skip: Number of resumes to skip
        limit: Number of resumes to return
        resume_service: Resume service

    Returns:
        List[ResumeResponse]: List of resumes
    """
    try:
        # Create filter using the API schema ResumeFilter
        filter_params = ResumeFilter(
            skip=skip,
            limit=limit,
        )

        # Get resumes
        resumes = await resume_service.filter_resumes(
            user_id=PydanticObjectId(current_user.id),
            filter_params=filter_params,
        )

        # Apply pagination manually since we're using API pagination
        paginated_resumes = resumes[skip : skip + limit]

        # Let Pydantic handle the conversion automatically
        return [ResumeResponse.model_validate(resume) for resume in paginated_resumes]

    except Exception as e:
        logger.error(f"Error getting resumes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get resumes",
        )


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
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
            user_id=PydanticObjectId(current_user.id),
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
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
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
            user_id=PydanticObjectId(current_user.id),
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
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
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
            user_id=PydanticObjectId(current_user.id),
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
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    job_description: str,
    selected_sections: List[str],
    current_user: CurrentUser,
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """
    Generate resume content based on job description.

    Args:
        resume_id: Resume ID
        job_description: Job description
        selected_sections: List of section names to generate
        current_user: Current authenticated user
        resume_generation_service: Resume generation service
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
            user_id=PydanticObjectId(current_user.id),
        )

        # Update job description if provided
        if job_description and job_description != resume.job_description:
            resume = await resume_service.update_resume(
                resume_id=resume_id,
                user_id=PydanticObjectId(current_user.id),
                update_data={"job_description": job_description},
            )

        # Generate resume content
        await resume_generation_service.generate_resume_content(
            resume_id=resume_id,
            regenerate_sections=selected_sections,
        )

        # Get updated resume
        updated_resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=PydanticObjectId(current_user.id),
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
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
) -> bytes:
    """
    Get resume as PDF.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_generation_service: Resume generation service

    Returns:
        bytes: PDF content

    Raises:
        HTTPException: If resume not found or PDF generation fails
    """
    try:
        # Generate PDF
        resume_latex, _ = await resume_generation_service.generate_latex(resume_id)
        pdf_content = await resume_generation_service.tex_service.compile_latex_to_pdf(
            resume_latex
        )

        logger.info(f"PDF generated for resume: {resume_id}")
        return pdf_content

    except Exception as e:
        logger.error(f"Error generating PDF for resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF",
        )
