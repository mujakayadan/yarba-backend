"""Resumes router."""

from datetime import datetime
from typing import Annotated, List, Optional

from beanie import PydanticObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from api.dependencies.auth import get_current_active_user
from api.dependencies.services import (
    get_cover_letter_service,
    get_portfolio_service,
    get_profile_service,
    get_resume_generation_service,
    get_resume_service,
)
from api.middleware.auth import CurrentUser
from api.schemas import (
    CoverLetterResponse,
    PaginatedResumeResponse,
    ResumeCreate,
    ResumeFilter,
    ResumeResponse,
    ResumeSelectionList,
    ResumeUpdate,
)
from api.schemas.resume import SortOptions
from config import get_logger
from core.exceptions.base import InternalServerException, NotFoundException
from core.models.resume import LLMUsageStats, Resume
from core.models.user import User
from core.services.cover_letter_service import CoverLetterService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService
from utils.storage import get_storage_provider

router = APIRouter()
logger = get_logger(__name__)


class ResumePDFResponse(BaseModel):
    """Response model for resume PDF URL."""

    pdf_url: Optional[str] = None


class ResumeLLMUsageResponse(BaseModel):
    """Response model for resume LLM usage statistics."""

    resume_id: str = Field(..., description="Resume ID")
    title: Optional[str] = Field(None, description="Resume title")
    company_name: Optional[str] = Field(None, description="Company name")
    job_title: Optional[str] = Field(None, description="Job title")
    usage: LLMUsageStats = Field(..., description="LLM usage statistics")
    created_at: datetime = Field(..., description="When the resume was created")
    updated_at: datetime = Field(..., description="When the resume was last updated")


def convert_resume_to_response(resume: Resume) -> ResumeResponse:
    """
    Convert a Resume model to a ResumeResponse schema, ensuring has_pdf is set correctly.

    Args:
        resume: Resume model instance

    Returns:
        ResumeResponse: API response model with correctly set has_pdf field
    """
    response = ResumeResponse.model_validate(resume)
    # Explicitly set has_pdf based on resume_pdf_key
    response.has_pdf = bool(resume.resume_pdf_key)
    return response


@router.get("/list-for-selection", response_model=ResumeSelectionList)
async def list_resumes_for_selection(
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
    sort_by: str = Query(
        SortOptions.UPDATED_DESC,
        description="Sort field and direction (e.g., updated_desc, title_asc)",
    ),
) -> ResumeSelectionList:
    """
    Get a list of resumes for selection, containing only ID and formatted name.
    """
    try:
        user_id = PydanticObjectId(current_user.id)
        selection_items = await resume_service.list_resumes_for_selection(
            user_id, sort_by=sort_by
        )
        return ResumeSelectionList(resumes=selection_items)
    except Exception as e:
        logger.error(f"Error listing resumes for selection: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list resumes for selection",
        )


@router.post("", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def create_resume(
    request: ResumeCreate,
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
    profile_service: ProfileService = Depends(get_profile_service),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
) -> ResumeResponse:
    """
    Create a new resume.

    Args:
        request: Resume creation request containing:
            - job_description: Required description of the job being applied for
            - compile_pdf: Optional boolean to trigger immediate PDF compilation (default: False)
        current_user: Current authenticated user
        resume_service: Resume service
        resume_generation_service: Resume generation service
        profile_service: Profile service
        portfolio_service: Portfolio service

    Returns:
        ResumeResponse: Created resume, with content and potentially a PDF link.

    Raises:
        HTTPException: If resume creation or subsequent generation/compilation fails.
    """
    try:
        user_id = PydanticObjectId(current_user.id)

        profile = await profile_service.get_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No profile found. Please create a profile first.",
            )

        portfolio = await portfolio_service.get_portfolio_by_user_id(user_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No portfolio found. Please create a portfolio first.",
            )

        # 1. Create the basic resume entry
        resume = await resume_service.create_resume(
            user_id=user_id,
            profile_id=profile.id,
            portfolio_id=portfolio.id,
            job_description=request.job_description,
            job_description_url=request.job_description_url,
        )
        logger.info(f"Resume record created: {resume.id}")

        # 2. Always populate textual content
        try:
            logger.info(f"Populating textual content for new resume: {resume.id}")
            await resume_generation_service.generate_resume_textual_content(
                resume_id=resume.id
            )
            # Refetch resume to get the populated content for potential PDF step or response
            resume_with_content = await resume_service.get_resume_by_id(
                resume.id, user_id
            )
            if not resume_with_content:
                raise InternalServerException(
                    f"Failed to refetch resume {resume.id} after content population."
                )
            resume = (
                resume_with_content  # Update resume variable to the one with content
            )
            logger.info(f"Textual content populated for resume: {resume.id}")
        except Exception as content_error:
            logger.error(
                f"Error populating content for new resume {resume.id}: {content_error}"
            )
            # Decide if we should raise immediately or allow creation of record without content
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Resume record created, but failed to populate text content: {content_error}",
            )

        # 3. Compile PDF if requested (and content should now be populated)
        if request.compile_pdf:
            if (
                not resume.content
            ):  # Should have been populated by the step above if compile_pdf is true
                logger.error(
                    f"Cannot compile PDF for resume {resume.id} as content is missing."
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot compile PDF: Text content was not populated or is missing.",
                )
            try:
                logger.info(f"Compiling PDF for new resume: {resume.id}")
                pdf_content = await resume_generation_service.compile_pdf(
                    resume, profile
                )  # Profile is already fetched

                if pdf_content:
                    storage_provider = get_storage_provider()
                    pdf_key = await storage_provider.save_resume_pdf(
                        pdf_content, str(resume.id)
                    )
                    update_data = ResumeUpdate(resume_pdf_key=pdf_key)
                    resume_with_pdf = await resume_service.update_resume(
                        resume_id=resume.id,
                        user_id=user_id,
                        update_data=update_data.model_dump(exclude_unset=True),
                    )
                    if not resume_with_pdf:
                        raise InternalServerException(
                            f"Failed to update resume {resume.id} with PDF key."
                        )
                    resume = resume_with_pdf  # Update resume variable to the one with PDF key
                    logger.info(f"PDF compiled and saved for resume: {resume.id}")
                else:
                    logger.warning(
                        f"PDF compilation returned empty content for resume: {resume.id}"
                    )
                    raise InternalServerException(
                        f"Failed to compile PDF content for resume {resume.id}"
                    )
            except Exception as pdf_error:
                logger.error(
                    f"Error compiling PDF for new resume {resume.id}: {pdf_error}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Resume created and content populated, but failed to compile PDF: {pdf_error}",
                )

        return convert_resume_to_response(resume)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error creating resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resume: {str(e)}",
        )


@router.get("", response_model=PaginatedResumeResponse)
async def get_resumes(
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="Number of resumes to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of resumes to return"),
    sort_by: str = Query("updated_desc", description="Sort field and direction"),
    search_term: Optional[str] = Query(
        None,
        description="Search term for title, company_name, job_title, and job_description",
    ),
    resume_service: ResumeService = Depends(get_resume_service),
) -> PaginatedResumeResponse:
    """
    Get all resumes for the current user.

    Args:
        current_user: Current authenticated user
        skip: Number of resumes to skip
        limit: Number of resumes to return
        sort_by: Sort field and direction
        search_term: Optional search term
        resume_service: Resume service

    Returns:
        PaginatedResumeResponse: List of resumes and total count
    """
    try:
        # Create filter
        filter_params = ResumeFilter(
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            search_term=search_term,
        )

        # Get resumes matching filter
        resumes = await resume_service.filter_resumes(
            user_id=PydanticObjectId(current_user.id),
            filter_params=filter_params,
        )

        # Count total matching filter (without pagination)
        total = await resume_service.count_resumes(
            user_id=PydanticObjectId(current_user.id),
            filter_params=filter_params,
        )

        # Convert resumes to response schema
        resume_responses = [convert_resume_to_response(resume) for resume in resumes]

        return PaginatedResumeResponse(
            items=resume_responses,
            total=total,
        )

    except Exception as e:
        logger.error(f"Error getting resumes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resumes: {str(e)}",
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

        return convert_resume_to_response(resume)

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
        user_id = PydanticObjectId(current_user.id)
        update_data_dict = request.model_dump(exclude_unset=True)
        # The job_description_url will be in update_data_dict if provided in the request
        updated_resume = await resume_service.update_resume(
            resume_id=resume_id, user_id=user_id, update_data=update_data_dict
        )
        if not updated_resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or update failed",
            )

        logger.info(f"Resume updated: {resume_id}")
        return convert_resume_to_response(updated_resume)

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
        resume_id: ID of the resume to delete
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        None

    Raises:
        HTTPException: If resume deletion fails
    """
    try:
        user_id = PydanticObjectId(current_user.id)
        await resume_service.delete_resume(resume_id, user_id)
        logger.info(f"Resume {resume_id} deleted successfully for user {user_id}")
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resume",
        )


@router.post("/{resume_id}/populate-text-content", response_model=ResumeResponse)
async def populate_resume_text_content(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeResponse:
    """
    Populate or update the complete textual content of an existing resume using LLM.
    This focuses only on the textual content, not PDF generation.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_generation_service: Resume generation service
        resume_service: Resume service

    Returns:
        ResumeResponse: Resume with updated textual content

    Raises:
        HTTPException: If content population fails or resume is not found
    """
    try:
        logger.info(f"Populating textual content for resume: {resume_id}")
        user_object_id = PydanticObjectId(current_user.id)

        # Get resume to ensure it exists and belongs to user
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=user_object_id,
        )
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Populate textual content using the renamed service method
        await resume_generation_service.generate_resume_textual_content(
            resume_id=resume_id,
        )

        # Get updated resume to return the latest state including generated content
        updated_resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=user_object_id,
        )
        if not updated_resume:  # Should not happen if the above was successful
            logger.error(
                f"Failed to refetch resume {resume_id} after content population."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated resume details.",
            )

        logger.info(f"Textual content populated for resume: {resume_id}")
        return convert_resume_to_response(updated_resume)

    except HTTPException:  # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            f"Error populating textual content for resume {resume_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to populate textual content: {str(e)}",
        )


@router.get(
    "/{resume_id}/pdf",
    response_model=ResumePDFResponse,
)
async def get_resume_pdf(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    timeout: int = Query(
        30,
        description="Timeout in seconds for PDF generation if needed",
        ge=5,  # Minimum 5 seconds
        le=60,  # Maximum 60 seconds
    ),
    resume_service: ResumeService = Depends(get_resume_service),
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
) -> ResumePDFResponse:
    """
    Get resume PDF URL from S3.

    NOTE: This endpoint returns a URL to the PDF file stored in S3, not the PDF content itself.
    Clients should use the returned URL to download or display the PDF.

    If the PDF doesn't exist yet, it will be generated and stored in S3 before returning the URL.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        timeout: Timeout in seconds for PDF generation if needed
        resume_service: Resume service
        resume_generation_service: Resume generation service

    Returns:
        ResumePDFResponse: Object containing the PDF URL
    """
    try:
        logger.info(f"Getting PDF URL for resume: {resume_id}")
        user_object_id = PydanticObjectId(current_user.id)

        # Get resume, profile, and portfolio data once
        try:
            resume, profile, portfolio = (
                await resume_generation_service.get_resume_data(resume_id)
            )
            # Verify ownership
            if resume.user_id != user_object_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User does not have permission to access this resume.",
                )
        except ValueError as e:
            logger.error(
                f"Error fetching data for resume {resume_id} in /get-resume-pdf: {e}"
            )
            if "not found" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve resume data.",
                )

        # Check if resume PDF is already stored in S3
        if resume.resume_pdf_key:
            logger.info(f"Resume PDF already exists in S3: {resume.resume_pdf_key}")

            # Get storage provider
            storage_provider = get_storage_provider()

            # Get the PDF URL
            pdf_url = storage_provider.get_url(resume.resume_pdf_key)

            if pdf_url:
                return ResumePDFResponse(pdf_url=pdf_url)
            else:
                logger.warning(
                    f"PDF key {resume.resume_pdf_key} found but failed to get URL. "
                    f"The PDF might be temporarily unavailable or the key is invalid."
                )
                # Do not attempt regeneration if a key exists but URL retrieval fails.
                # This indicates an issue with storage or the key itself, not that the PDF doesn't exist.
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="PDF is temporarily unavailable or the stored key is invalid. Please try again later.",
                )

        # No S3 PDF exists, generate a new one
        logger.info(f"No PDF key found for resume: {resume_id}, generating new one.")

        # Use asyncio.wait_for to implement timeout
        import asyncio

        pdf_content = None

        try:
            # Generate PDF content by calling compile_pdf with fetched objects
            logger.info(f"Compiling PDF for resume: {resume_id}")
            pdf_content = await asyncio.wait_for(
                resume_generation_service.compile_pdf(resume, profile),
                timeout=timeout,  # Use full timeout for compilation now
            )
        except asyncio.TimeoutError:
            logger.error(
                f"PDF compilation timed out after {timeout} seconds for resume: {resume_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="PDF generation timed out during compilation. Please try again later.",
            )
        except ValueError as e:
            logger.error(f"PDF compilation failed for resume {resume_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to compile PDF: {e}",
            )

        # Check if PDF was generated
        if not pdf_content:
            logger.error(f"PDF compilation returned None for resume: {resume_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF generation failed - no content returned",
            )

        logger.info(
            f"PDF generated for resume: {resume_id}, size: {len(pdf_content)} bytes"
        )

        # Save PDF to S3
        try:
            storage_provider = get_storage_provider()
            pdf_key = await storage_provider.save_resume_pdf(
                pdf_content, str(resume.id)
            )

            # Update resume with the new PDF key using ResumeService
            update_data = ResumeUpdate(resume_pdf_key=pdf_key)
            await resume_service.update_resume(
                resume_id=resume_id,
                user_id=user_object_id,
                update_data=update_data.model_dump(exclude_unset=True),
            )

            logger.info(f"PDF saved to S3: {pdf_key}")

            # Get the URL for the PDF
            pdf_url = storage_provider.get_url(pdf_key)
            return ResumePDFResponse(pdf_url=pdf_url)

        except Exception as s3_error:
            logger.error(f"Error saving PDF to S3: {str(s3_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save PDF to storage: {str(s3_error)}",
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error generating PDF for resume {resume_id}: {str(e)}")
        # Print full traceback
        import traceback

        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}",
        )


@router.post("/{resume_id}/debug-pdf")
async def debug_pdf_generation(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
) -> dict:
    """
    DEBUG endpoint to test PDF generation directly.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_service: Resume service
        resume_generation_service: Resume generation service

    Returns:
        dict: Debug information
    """
    try:
        # Get the resume
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id, user_id=PydanticObjectId(current_user.id)
        )

        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Get profile using the resume_generation_service instead
        # The resume_generation_service already has access to profile_repository
        _, profile, _ = await resume_generation_service.get_resume_data(resume_id)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Debug information
        debug_info = {
            "resume_id": str(resume.id),
            "profile_id": str(resume.profile_id),
            "content_exists": bool(resume.content),
            "content_keys": list(resume.content.keys()) if resume.content else [],
            "steps": [],
        }

        try:
            # Step 1: Generate LaTeX
            logger.info("DEBUG: Step 1 - Generate LaTeX")
            latex_content = await resume_generation_service.generate_latex(resume_id)
            debug_info["steps"].append(
                {
                    "step": "generate_latex",
                    "success": bool(latex_content),
                    "length": len(latex_content) if latex_content else 0,
                }
            )

            # Step 2: Compile PDF
            logger.info("DEBUG: Step 2 - Compile PDF")
            pdf_content = await resume_generation_service.compile_pdf(resume_id)
            debug_info["steps"].append(
                {
                    "step": "compile_pdf",
                    "success": bool(pdf_content),
                    "size": len(pdf_content) if pdf_content else 0,
                }
            )

            # Check if PDF is now stored in resume
            updated_resume = await resume_service.get_resume_by_id(
                resume_id=resume_id, user_id=PydanticObjectId(current_user.id)
            )
            debug_info["pdf_stored_in_s3"] = bool(updated_resume.resume_pdf_key)
            debug_info["pdf_key"] = (
                updated_resume.resume_pdf_key if updated_resume.resume_pdf_key else None
            )

            debug_info["success"] = True

        except Exception as step_error:
            debug_info["error"] = str(step_error)
            debug_info["success"] = False
            logger.error(f"DEBUG PDF Generation Error: {step_error}")
            import traceback

            debug_info["traceback"] = traceback.format_exc()

        return debug_info

    except Exception as e:
        logger.error(f"Error in debug PDF generation: {str(e)}")
        import traceback

        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug PDF generation failed: {str(e)}",
        )


@router.post("/{resume_id}/regenerate", response_model=ResumeResponse)
async def regenerate_resume(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    generate_pdf: bool = Query(
        True, description="Whether to regenerate the PDF as well"
    ),
    resume_service: ResumeService = Depends(get_resume_service),
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
    profile_service: ProfileService = Depends(get_profile_service),
) -> ResumeResponse:
    """
    Regenerate a resume.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        generate_pdf: Whether to regenerate the PDF as well
        resume_service: Resume service
        resume_generation_service: Resume generation service
        profile_service: Profile service

    Returns:
        ResumeResponse: Regenerated resume

    Raises:
        HTTPException: If resume regeneration fails
    """
    try:
        logger.info(f"Regenerating resume: {resume_id}")
        user_object_id = PydanticObjectId(current_user.id)

        # Get resume to ensure it exists and belongs to user
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=user_object_id,
        )
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
            )

        # Generate content using the unified method
        await resume_generation_service.generate_resume_textual_content(
            resume_id=resume_id,
        )

        # If PDF regeneration is requested, generate PDF
        if generate_pdf:
            try:
                logger.info(f"Regenerating PDF for resume: {resume_id}")

                # Refetch resume to get the latest content for PDF generation
                resume_after_content_gen = await resume_service.get_resume_by_id(
                    resume_id=resume_id,
                    user_id=user_object_id,
                )
                if not resume_after_content_gen:
                    logger.error(
                        f"Failed to refetch resume {resume_id} after content generation for PDF."
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to retrieve updated resume data for PDF generation.",
                    )

                # Refetch profile for PDF generation
                profile = await profile_service.get_profile_by_id(
                    resume_after_content_gen.profile_id  # Use profile_id from the latest resume
                )
                if not profile:
                    logger.error(
                        f"Profile {resume_after_content_gen.profile_id} not found for resume {resume_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Profile not found",
                    )

                # Generate PDF content using the latest resume data
                pdf_content = await resume_generation_service.compile_pdf(
                    resume_after_content_gen, profile
                )

                if not pdf_content:
                    logger.error(
                        f"PDF generation returned empty content for resume: {resume_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="PDF generation failed: Empty content",
                    )

                # Save PDF to S3
                storage_provider = get_storage_provider()
                pdf_key = await storage_provider.save_resume_pdf(
                    pdf_content, str(resume_id)
                )

                # Update resume with the new PDF key
                update_data = ResumeUpdate(resume_pdf_key=pdf_key)
                await resume_service.update_resume(  # No need to assign to 'resume' here, final fetch is done later
                    resume_id=resume_id,  # Use resume_id consistently
                    user_id=user_object_id,
                    update_data=update_data.model_dump(exclude_unset=True),
                )

                logger.info(f"PDF regenerated and saved for resume: {resume_id}")

            except Exception as pdf_error:
                logger.error(
                    f"Error regenerating PDF for resume {resume_id}: {str(pdf_error)}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to regenerate PDF: {str(pdf_error)}",
                )

        # Get final updated resume to return the latest state
        final_updated_resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=user_object_id,
        )
        if not final_updated_resume:  # Check if the final fetch was successful
            logger.error(
                f"Failed to retrieve final resume state for {resume_id} after all operations."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve final resume details.",
            )

        logger.info(f"Resume regenerated: {resume_id}")
        return convert_resume_to_response(final_updated_resume)

    except HTTPException:  # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error regenerating resume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate resume: {str(e)}",
        )


@router.post("/{resume_id}/upload-pdf", response_model=ResumePDFResponse)
async def upload_resume_pdf(
    resume_id: PydanticObjectId = Path(..., description="Resume ID"),
    file: UploadFile = File(..., description="PDF file to upload"),
    current_user: User = Depends(get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """
    Upload a PDF file for a resume directly instead of generating it.

    Args:
        resume_id: Resume ID
        file: PDF file to upload
        current_user: Current authenticated user
        resume_service: Resume service

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
        # Get the resume
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=PydanticObjectId(current_user.id),
        )

        # Read the file content
        content = await file.read()

        # Get storage provider
        storage_provider = get_storage_provider()

        # If resume already has a PDF stored in S3, delete it
        if resume.resume_pdf_key:
            try:
                await storage_provider.delete_file(resume.resume_pdf_key)
                logger.info(f"Deleted previous PDF from S3: {resume.resume_pdf_key}")
            except Exception as delete_error:
                logger.error(f"Error deleting previous PDF: {str(delete_error)}")

        # Save the new PDF to S3
        pdf_key = await storage_provider.save_resume_pdf(content, str(resume_id))
        logger.info(f"Saved new PDF to S3: {pdf_key}")

        # Update resume with the new PDF key
        await resume_service.update_resume(
            resume_id=resume_id,
            user_id=PydanticObjectId(current_user.id),
            update_data={"resume_pdf_key": pdf_key},  # Only update the key
        )

        logger.info(f"PDF saved to S3: {pdf_key}")

        # Get the URL for the PDF
        pdf_url = storage_provider.get_url(pdf_key)
        return {"pdf_url": pdf_url}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    except Exception as e:
        logger.error(f"Error uploading resume PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload resume PDF: {str(e)}",
        )


@router.delete("/{resume_id}/pdf", response_model=ResumePDFResponse)
async def delete_resume_pdf(
    resume_id: PydanticObjectId = Path(..., description="Resume ID"),
    current_user: User = Depends(get_current_active_user),
    resume_service: ResumeService = Depends(get_resume_service),
):
    """
    Delete the PDF file for a resume.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        Empty PDF URL
    """
    try:
        # Get the resume
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=PydanticObjectId(current_user.id),
        )

        # Get storage provider
        storage_provider = get_storage_provider()

        # If resume has a PDF in S3, delete it
        if resume.resume_pdf_key:
            try:
                success = await storage_provider.delete_file(resume.resume_pdf_key)
                if success:
                    logger.info(f"Deleted PDF from S3: {resume.resume_pdf_key}")
                else:
                    logger.warning(
                        f"Failed to delete PDF from S3: {resume.resume_pdf_key}"
                    )
            except Exception as e:
                logger.error(f"Error deleting PDF from S3: {str(e)}")

            # Update resume to remove PDF references
            await resume_service.update_resume(
                resume_id=resume_id,
                user_id=PydanticObjectId(current_user.id),
                update_data={
                    "resume_pdf_key": None,
                },
            )

        return {"pdf_url": None}

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    except Exception as e:
        logger.error(f"Error deleting resume PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume PDF: {str(e)}",
        )


@router.get(
    "/{resume_id}/cover-letters",
    response_model=List[CoverLetterResponse],
    summary="Get cover letters for a resume",
)
async def get_resume_cover_letters(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
) -> List[CoverLetterResponse]:
    """
    Get all cover letters associated with a resume.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_service: Resume service
        cover_letter_service: Cover letter service

    Returns:
        List[CoverLetterResponse]: List of cover letters associated with the resume

    Raises:
        HTTPException: If resume not found or doesn't belong to the user
    """
    try:
        # Verify resume exists and belongs to user
        await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=PydanticObjectId(current_user.id),
        )

        # Get cover letters by resume ID
        filter_params = CoverLetterFilter(
            resume_id=resume_id,
            limit=100,  # Get all cover letters for this resume
        )

        cover_letters = await cover_letter_service.filter_cover_letters(
            user_id=PydanticObjectId(current_user.id),
            filter_params=filter_params,
        )

        # Convert to response format
        from api.routers.cover_letters import convert_cover_letter_to_response

        cover_letter_responses = [
            convert_cover_letter_to_response(cover_letter)
            for cover_letter in cover_letters
        ]

        return cover_letter_responses

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    except Exception as e:
        logger.error(f"Error getting cover letters for resume {resume_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cover letters",
        )


@router.get("/{resume_id}/llm-usage", response_model=ResumeLLMUsageResponse)
async def get_resume_llm_usage(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
) -> ResumeLLMUsageResponse:
    """
    Get LLM usage statistics for a specific resume.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_service: Resume service

    Returns:
        Resume LLM usage statistics

    Raises:
        HTTPException: If resume is not found or access is denied
    """
    try:
        # Get resume with usage statistics
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id,
            user_id=PydanticObjectId(current_user.id),
        )

        # Return usage data along with basic resume info
        return {
            "resume_id": str(resume.id),
            "title": resume.title,
            "company_name": resume.company_name,
            "job_title": resume.job_title,
            "usage": resume.llm_usage,
            "created_at": resume.created_at,
            "updated_at": resume.updated_at,
        }

    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )
    except Exception as e:
        logger.error(f"Error retrieving resume LLM usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve resume LLM usage: {str(e)}",
        )
