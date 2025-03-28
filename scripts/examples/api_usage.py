"""Example demonstrating how to use the resume services with FastAPI."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

# These would be imported in your actual API code
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService


# Example request models
class GenerateResumeRequest(BaseModel):
    """Request model for generating a resume."""

    user_id: str = Field(..., description="User ID")
    resume_id: str = Field(..., description="Resume ID")


class GenerateCoverLetterRequest(BaseModel):
    """Request model for generating a cover letter."""

    user_id: str = Field(..., description="User ID")
    resume_id: str = Field(..., description="Resume ID")


class GenerationResponse(BaseModel):
    """Response model for generated content."""

    latex: str = Field(..., description="Generated LaTeX content")
    preview_text: Optional[str] = Field(
        None, description="Preview of the generated content"
    )


# Create dependencies for service injection
async def get_resume_generation_service():
    """Dependency for resume generation service."""
    # Initialize repositories
    portfolio_repository = PortfolioRepository()
    profile_repository = ProfileRepository()
    resume_repository = ResumeRepository()
    tex_template_repository = TexTemplateRepository()
    tex_header_repository = TexHeaderRepository()

    # Initialize services
    prompt_service = PromptService()
    llm_service = LLMService(
        profile_repository=profile_repository, prompt_service=prompt_service
    )
    latex_service = LatexService(preamble_repository=PreambleRepository)

    # Initialize resume generation service
    return ResumeGenerationService(
        resume_repository=resume_repository,
        portfolio_repository=portfolio_repository,
        profile_repository=profile_repository,
        llm_service=llm_service,
        latex_service=latex_service,
    )


# Example FastAPI router
router = APIRouter(prefix="/api/v1/generation", tags=["Resume Generation"])


@router.post("/resume", response_model=GenerationResponse)
async def generate_resume(
    request: GenerateResumeRequest,
    resume_service: ResumeGenerationService = Depends(get_resume_generation_service),
):
    """Generate a resume for a user."""
    try:
        # Configure service for the user
        await resume_service.configure_for_user(request.user_id)

        # Generate resume content
        resume_content = await resume_service.generate_resume_content(request.resume_id)

        # Generate LaTeX
        latex = await resume_service.generate_latex(
            resume_id=request.resume_id, content=resume_content, is_cover_letter=False
        )

        # Extract a preview (first 150 characters of the first section)
        first_section = next(iter(resume_content.values()), "")
        preview = (
            first_section[:150] + "..." if len(first_section) > 150 else first_section
        )

        return GenerationResponse(latex=latex, preview_text=preview)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating resume: {str(e)}"
        )


@router.post("/cover-letter", response_model=GenerationResponse)
async def generate_cover_letter(
    request: GenerateCoverLetterRequest,
    resume_service: ResumeGenerationService = Depends(get_resume_generation_service),
):
    """Generate a cover letter for a user."""
    try:
        # Configure service for the user
        await resume_service.configure_for_user(request.user_id)

        # Generate resume content (needed for cover letter)
        resume_content = await resume_service.generate_resume_content(request.resume_id)

        # Generate cover letter
        cover_letter = await resume_service.generate_cover_letter(
            resume_id=request.resume_id, resume_content=resume_content
        )

        # Generate LaTeX
        latex = await resume_service.generate_latex(
            resume_id=request.resume_id, content=cover_letter, is_cover_letter=True
        )

        # Extract a preview (first 150 characters)
        preview = (
            cover_letter[:150] + "..." if len(cover_letter) > 150 else cover_letter
        )

        return GenerationResponse(latex=latex, preview_text=preview)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating cover letter: {str(e)}"
        )


# How to add this router to your FastAPI app
def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Resume Builder API", version="1.0.0")
    app.include_router(router)
    return app


# To run this with uvicorn:
# uvicorn scripts.examples.api_usage:create_app() --reload
