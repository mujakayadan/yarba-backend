"""Resumes router."""

from datetime import datetime
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
        logger.info(f"Starting PDF generation for resume: {resume_id}")

        # Generate LaTeX
        logger.info(f"Generating LaTeX for resume: {resume_id}")
        resume_latex = await resume_generation_service.generate_latex(resume_id)
        logger.info(
            f"LaTeX generated for resume: {resume_id}, length: {len(resume_latex)} bytes"
        )

        # Compile PDF
        logger.info(f"Compiling PDF for resume: {resume_id}")
        pdf_content = await resume_generation_service.compile_pdf(resume_id)

        # Check if PDF was generated
        if pdf_content:
            logger.info(
                f"PDF generated for resume: {resume_id}, size: {len(pdf_content)} bytes"
            )
        else:
            logger.error(f"PDF compilation returned None for resume: {resume_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF generation failed - no content returned",
            )

        return pdf_content

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

        # Get profile
        profile = await resume_service.repository.profile_repository.get_by_id(
            resume.profile_id
        )
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
            debug_info["pdf_stored_in_db"] = bool(updated_resume.resume_pdf)
            debug_info["pdf_size_in_db"] = (
                len(updated_resume.resume_pdf) if updated_resume.resume_pdf else 0
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


@router.post("/{resume_id}/advanced-debug")
async def advanced_debug_pdf_generation(
    resume_id: Annotated[PydanticObjectId, Path(description="Resume ID")],
    current_user: CurrentUser,
    resume_service: ResumeService = Depends(get_resume_service),
    resume_generation_service: ResumeGenerationService = Depends(
        get_resume_generation_service
    ),
) -> dict:
    """
    Advanced DEBUG endpoint to trace through the entire PDF generation process.

    Args:
        resume_id: Resume ID
        current_user: Current authenticated user
        resume_service: Resume service
        resume_generation_service: Resume generation service

    Returns:
        dict: Detailed debug information
    """
    import inspect
    import json
    import traceback

    from pydantic import BaseModel

    debug_info = {
        "resume_id": str(resume_id),
        "user_id": current_user.id,
        "process_steps": [],
        "errors": [],
        "success": False,
        "data_snapshots": {},
    }

    def add_step(name, status="started", details=None):
        step = {"step": name, "status": status, "timestamp": datetime.now().isoformat()}
        if details:
            step["details"] = details
        debug_info["process_steps"].append(step)
        logger.info(f"DEBUG STEP: {name} - {status}")
        if details:
            logger.info(f"DETAILS: {json.dumps(details, default=str)}")

    def add_error(step, error, traceback_info=None):
        error_info = {
            "step": step,
            "error": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback_info or traceback.format_exc(),
        }
        debug_info["errors"].append(error_info)
        logger.error(f"DEBUG ERROR in {step}: {error}")
        logger.error(traceback_info or traceback.format_exc())

    def safe_object_to_dict(obj):
        """Safely convert an object to a dictionary, handling PydanticObjectId instances."""
        if isinstance(obj, BaseModel):
            # Convert Pydantic model to dict
            return {k: safe_object_to_dict(v) for k, v in obj.model_dump().items()}
        elif hasattr(obj, "__dict__"):
            # Handle regular objects
            result = {}
            for k, v in obj.__dict__.items():
                if not k.startswith("_"):  # Skip private attributes
                    result[k] = safe_object_to_dict(v)
            return result
        elif isinstance(obj, list):
            return [safe_object_to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: safe_object_to_dict(v) for k, v in obj.items()}
        elif isinstance(obj, PydanticObjectId):
            return str(obj)
        else:
            # For other types, try to serialize to string or return a placeholder
            try:
                return str(obj)
            except:
                return f"<{type(obj).__name__} - unserializable>"

    try:
        add_step("Fetching resume")

        # Get the resume
        resume = await resume_service.get_resume_by_id(
            resume_id=resume_id, user_id=PydanticObjectId(current_user.id)
        )

        if not resume:
            add_step("Fetching resume", "error", {"error": "Resume not found"})
            debug_info["success"] = False
            return debug_info

        add_step(
            "Fetching resume",
            "success",
            {
                "title": resume.title,
                "content_keys": list(resume.content.keys()) if resume.content else [],
            },
        )

        # Add snapshot of resume data
        debug_info["data_snapshots"]["resume"] = {
            "id": str(resume.id),
            "title": resume.title,
            "user_id": str(resume.user_id),
            "profile_id": str(resume.profile_id),
            "portfolio_id": str(resume.portfolio_id),
            "has_content": bool(resume.content),
            "content_keys": list(resume.content.keys()) if resume.content else [],
            "has_pdf": bool(resume.resume_pdf),
            "pdf_size": len(resume.resume_pdf) if resume.resume_pdf else 0,
        }

        # Get profile
        add_step("Fetching profile")
        profile = await resume_service.repository.profile_repository.get_by_id(
            resume.profile_id
        )
        if not profile:
            add_step("Fetching profile", "error", {"error": "Profile not found"})
            debug_info["success"] = False
            return debug_info

        add_step("Fetching profile", "success", {"name": profile.full_name})

        # Add snapshot of profile data
        debug_info["data_snapshots"]["profile"] = {
            "id": str(profile.id),
            "full_name": profile.full_name,
            "email": profile.email,
        }

        # Get portfolio
        add_step("Fetching portfolio")
        portfolio = await resume_service.repository.portfolio_repository.get_by_id(
            resume.portfolio_id
        )
        if not portfolio:
            add_step("Fetching portfolio", "error", {"error": "Portfolio not found"})
            debug_info["success"] = False
            return debug_info

        add_step("Fetching portfolio", "success", {"user_id": str(portfolio.user_id)})

        # Step-by-step debugging through the entire process
        try:
            # 1. Generate resume content if needed
            if not resume.content or not resume.content.get("personal_information"):
                add_step("Generating resume content", "started")
                try:
                    content = await resume_generation_service.generate_resume_content(
                        resume_id
                    )
                    add_step(
                        "Generating resume content",
                        "success",
                        {"content_keys": list(content.keys())},
                    )
                except Exception as e:
                    add_step("Generating resume content", "error", {"error": str(e)})
                    add_error("Generating resume content", e)
                    # Continue with other steps even if content generation fails
            else:
                add_step(
                    "Generating resume content",
                    "skipped",
                    {"reason": "Content already exists"},
                )

            # 2. Get updated resume after content generation
            add_step("Fetching updated resume")
            updated_resume = await resume_service.get_resume_by_id(
                resume_id=resume_id, user_id=PydanticObjectId(current_user.id)
            )

            debug_info["data_snapshots"]["updated_resume"] = {
                "has_content": bool(updated_resume.content),
                "content_keys": (
                    list(updated_resume.content.keys())
                    if updated_resume.content
                    else []
                ),
            }

            # 3. Generate LaTeX
            add_step("Generating LaTeX", "started")
            try:
                # Save a sample of the content data before conversion
                for section_name, section_data in updated_resume.content.items():
                    if not isinstance(section_data, str):
                        sample_data = safe_object_to_dict(section_data)
                        add_step(
                            "Content sample",
                            "info",
                            {
                                "section": section_name,
                                "data_type": type(section_data).__name__,
                                "sample": (
                                    str(sample_data)[:500] + "..."
                                    if len(str(sample_data)) > 500
                                    else str(sample_data)
                                ),
                            },
                        )

                # Debug the _convert_to_serializable method
                add_step("Testing serialization", "started")
                try:
                    # Test serialization with a sample that includes PydanticObjectId
                    test_data = {
                        "id": resume_id,
                        "nested": {"id": resume_id},
                        "list": [resume_id, {"id": resume_id}],
                    }
                    serialized = resume_generation_service._convert_to_serializable(
                        test_data
                    )
                    add_step(
                        "Testing serialization", "success", {"serialized": serialized}
                    )
                except Exception as e:
                    add_step("Testing serialization", "error", {"error": str(e)})
                    add_error("Testing serialization", e)

                # Generate LaTeX
                latex_content = await resume_generation_service.generate_latex(
                    resume_id
                )
                latex_preview = (
                    latex_content[:500] + "..."
                    if len(latex_content) > 500
                    else latex_content
                )
                add_step(
                    "Generating LaTeX",
                    "success",
                    {"length": len(latex_content), "preview": latex_preview},
                )

                # 4. Compile PDF
                add_step("Compiling PDF", "started")
                pdf_content = await resume_generation_service.compile_pdf(resume_id)
                add_step(
                    "Compiling PDF",
                    "success",
                    {"size": len(pdf_content) if pdf_content else 0},
                )

                # 5. Check if PDF was saved in resume
                add_step("Checking saved PDF")
                final_resume = await resume_service.get_resume_by_id(
                    resume_id=resume_id, user_id=PydanticObjectId(current_user.id)
                )

                pdf_saved = bool(final_resume.resume_pdf)
                pdf_size = (
                    len(final_resume.resume_pdf) if final_resume.resume_pdf else 0
                )

                add_step(
                    "Checking saved PDF",
                    "success" if pdf_saved else "warning",
                    {"pdf_saved": pdf_saved, "pdf_size": pdf_size},
                )

                debug_info["success"] = pdf_saved and pdf_size > 0

            except Exception as step_error:
                add_error("PDF generation process", step_error)
                debug_info["success"] = False

        except Exception as process_error:
            add_error("Overall process", process_error)
            debug_info["success"] = False

        return debug_info

    except Exception as e:
        add_error("Initialization", e)
        debug_info["success"] = False
        return debug_info
