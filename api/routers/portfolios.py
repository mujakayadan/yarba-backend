"""Portfolio router for the API."""

from datetime import UTC, datetime
from typing import Annotated, Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from pydantic import BaseModel

from config.logging_config import get_logger
from core.database import get_portfolio_repository, get_unit_of_work
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.models.portfolio import (
    Award,
    CareerSummary,
    CustomSections,
    Education,
    Portfolio,
    Project,
    Publication,
    Skill,
    WorkExperience,
)
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.services.document_parser_service import DocumentParserService
from core.services.llm_service import LLMService
from core.utils.object_id import coerce_object_id, require_object_id

from ..dependencies.auth import CurrentActiveUser

router = APIRouter()
logger = get_logger(__name__)


# Dependency for ProfileRepository (assuming you have a standard way to get this)
# If not, you might need to create one or adjust based on your DI pattern.
def get_profile_repository() -> ProfileRepository:
    # This is a placeholder. Replace with your actual ProfileRepository instantiation/retrieval.
    # For example, if it's a simple class:
    return ProfileRepository()


# Dependency for LLMService
def get_llm_service(
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> LLMService:
    # LLMService might have default model/temp, or you can configure from settings
    return LLMService(profile_repository=profile_repo)


# Updated Dependency for DocumentParserService
def get_document_parser_service(
    llm_service: LLMService = Depends(get_llm_service),
) -> DocumentParserService:
    return DocumentParserService(llm_service=llm_service)


class PortfolioCreate(BaseModel):
    """Portfolio creation model."""

    profile_id: str | None = None
    career_summary: CareerSummary | None = None
    skills: list[Skill] | None = None
    work_experience: list[WorkExperience] | None = None
    education: list[Education] | None = None
    projects: list[Project] | None = None
    awards: list[Award] | None = None
    publications: list[Publication] | None = None
    certifications: list[Any] | None = None
    custom_sections: CustomSections | None = None


class PortfolioUpdate(BaseModel):
    """Portfolio update model."""

    profile_id: str | None = None
    career_summary: CareerSummary | None = None
    skills: list[Skill] | None = None
    work_experience: list[WorkExperience] | None = None
    education: list[Education] | None = None
    projects: list[Project] | None = None
    awards: list[Award] | None = None
    publications: list[Publication] | None = None
    certifications: list[str] | None = None
    custom_sections: CustomSections | None = None
    is_active: bool | None = None
    version: str | None = None


class PortfolioPatchOperation(BaseModel):
    """Schema for a portfolio patch operation."""

    # Optional fields that can be individually updated
    career_summary: CareerSummary | None = None
    skills: list[Skill] | None = None
    work_experience: list[WorkExperience] | None = None
    education: list[Education] | None = None
    projects: list[Project] | None = None
    awards: list[Award] | None = None
    publications: list[Publication] | None = None
    certifications: list[str] | None = None
    custom_sections: CustomSections | None = None
    is_active: bool | None = None
    version: str | None = None
    profile_id: str | None = None


@router.get("/", response_model=Portfolio)
async def get_portfolios(
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Get the portfolio for the current user.

    Args:
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        The user's portfolio or raises 404 if not found
    """
    portfolio = await portfolio_repository.get_by_user(current_user)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )
    return portfolio


@router.post("/", response_model=Portfolio, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    current_user: CurrentActiveUser,
):
    """Create a new portfolio.

    Args:
        portfolio_data: Portfolio data
        current_user: Current authenticated user

    Returns:
        Created portfolio
    """
    db_profile_id: PydanticObjectId | None = None
    if portfolio_data.profile_id:
        try:
            db_profile_id = PydanticObjectId(portfolio_data.profile_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid profile_id format: {portfolio_data.profile_id}",
            )

    # Prepare creation data from portfolio_data, excluding profile_id as it's handled separately
    # and ensuring only fields explicitly set by the client (and not None) are passed.
    # Beanie's default_factory will handle fields not provided or explicitly set to None if Pydantic doesn't set them.
    create_kwargs = portfolio_data.model_dump(
        exclude_unset=True, exclude_none=False
    )  # Pass None to allow explicit nulling if model supports it

    # Remove profile_id from create_kwargs as it's passed directly to the Portfolio constructor
    if "profile_id" in create_kwargs:
        del create_kwargs["profile_id"]

    # Create the Portfolio document instance
    # Beanie models can typically accept Pydantic model instances for nested fields
    # or dictionaries. model_dump(exclude_unset=True) helps pass only provided data.
    try:
        portfolio = Portfolio(
            user_id=current_user.id,
            profile_id=db_profile_id,
            **create_kwargs,  # Pass all other valid fields from PortfolioCreate
        )
    except Exception as e:
        logger.error(f"Error instantiating Portfolio model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating portfolio data.",
        )

    await portfolio.create()
    return portfolio


@router.get("/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Get a portfolio by ID.

    Args:
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio",
        )

    return portfolio


@router.put("/{portfolio_id}", response_model=Portfolio)
async def update_portfolio(
    portfolio_data: PortfolioUpdate,
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update a portfolio.

    Args:
        portfolio_data: Portfolio data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update career summary if provided
    if portfolio_data.career_summary:
        portfolio.career_summary = portfolio_data.career_summary

    # Update portfolio fields
    for field, value in portfolio_data.model_dump(exclude_unset=True).items():
        if field != "career_summary":  # Skip career summary as it's handled above
            setattr(portfolio, field, value)

    await portfolio.save()
    return portfolio


@router.patch("/{portfolio_id}", response_model=Portfolio)
async def patch_portfolio(
    portfolio_data: PortfolioPatchOperation,
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Partially update a portfolio (only specified fields).

    Args:
        portfolio_data: Portfolio data to patch
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update only the fields that were provided in the request
    patch_data = portfolio_data.model_dump(exclude_unset=True)

    # Handle special case for career_summary which needs to be instantiated as a model
    if "career_summary" in patch_data:
        portfolio.career_summary = CareerSummary.model_validate(
            patch_data.pop("career_summary")
        )

    # Update remaining portfolio fields
    for field, value in patch_data.items():
        setattr(portfolio, field, value)

    # Update the timestamp
    portfolio.updated_at = datetime.now(UTC)

    await portfolio.save()
    return portfolio


@router.patch("/{portfolio_id}/career-summary", response_model=Portfolio)
async def patch_career_summary(
    career_summary: CareerSummary,
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update only the career summary section of a portfolio.

    Args:
        career_summary: Career summary data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update career summary
    await portfolio_repository.update_career_summary(
        require_object_id(portfolio.id), career_summary
    )

    # Return updated portfolio
    return await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))


@router.patch("/{portfolio_id}/skills", response_model=Portfolio)
async def patch_skills(
    skills: list[Skill],
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update only the skills section of a portfolio.

    Args:
        skills: Skills data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update skills
    await portfolio_repository.update_skills(require_object_id(portfolio.id), skills)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))


@router.patch("/{portfolio_id}/work-experience", response_model=Portfolio)
async def patch_work_experience(
    work_experience: list[WorkExperience],
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update only the work experience section of a portfolio.

    Args:
        work_experience: Work experience data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update work experience
    await portfolio_repository.update_work_experience(
        require_object_id(portfolio.id), work_experience
    )

    # Return updated portfolio
    return await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))


@router.patch("/{portfolio_id}/education", response_model=Portfolio)
async def patch_education(
    education: list[Education],
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update only the education section of a portfolio.

    Args:
        education: Education data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update education
    await portfolio_repository.update_education(
        require_object_id(portfolio.id), education
    )

    # Return updated portfolio
    return await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))


@router.patch("/{portfolio_id}/projects", response_model=Portfolio)
async def patch_projects(
    projects: list[Project],
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update only the projects section of a portfolio.

    Args:
        projects: Projects data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update projects
    await portfolio_repository.update_projects(
        require_object_id(portfolio.id), projects
    )

    # Return updated portfolio
    return await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))


@router.patch("/{portfolio_id}/awards", response_model=Portfolio)
async def patch_awards(
    awards: list[Award],
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update only the awards section of a portfolio.

    Args:
        awards: Awards data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update awards
    await portfolio_repository.update_awards(require_object_id(portfolio.id), awards)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))


@router.patch("/{portfolio_id}/publications", response_model=Portfolio)
async def patch_publications(
    publications: list[Publication],
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Update only the publications section of a portfolio.

    Args:
        publications: Publications data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this portfolio",
        )

    # Update publications
    await portfolio_repository.update_publications(
        require_object_id(portfolio.id), publications
    )

    # Return updated portfolio
    return await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: Annotated[str, Path(..., description="Portfolio ID")],
    current_user: CurrentActiveUser,
    uow: AsyncMongoUnitOfWork = Depends(get_unit_of_work),
):
    """Delete a portfolio.

    Args:
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        uow: Unit of work

    Returns:
        None
    """
    async with uow:
        portfolio_repository = uow.portfolio_repository
        if portfolio_repository is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Portfolio repository unavailable",
            )

        portfolio = await portfolio_repository.get_by_id(coerce_object_id(portfolio_id))
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found",
            )

        # Check if the portfolio belongs to the current user
        if portfolio.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this portfolio",
            )

        await portfolio.delete()


@router.get("/by-profile/{profile_id}", response_model=Portfolio)
async def get_portfolio_by_profile(
    profile_id: Annotated[str, Path(..., description="Profile ID")],
    current_user: CurrentActiveUser,
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """Get a portfolio by profile ID.

    Args:
        profile_id: Profile ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Portfolio
    """
    portfolio = await portfolio_repository.get_by_profile_id(
        coerce_object_id(profile_id)
    )
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio",
        )

    return portfolio


@router.post(
    "/parse-document", response_model=Portfolio, status_code=status.HTTP_200_OK
)
async def parse_portfolio_document(
    current_user: CurrentActiveUser,
    file: UploadFile = File(
        ..., description="Portfolio document (PDF or DOCX) to upload and parse."
    ),
    parser_service: DocumentParserService = Depends(get_document_parser_service),
):
    """Uploads a portfolio document (PDF, DOCX), parses its content,
    and returns a Portfolio data structure based on the parsed information.
    This endpoint DOES NOT save the portfolio to the database.
    The returned data can be used to subsequently create or update a portfolio.
    """
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF and DOCX files are accepted.",
        )

    try:
        parsed_data_dict = await parser_service.parse_to_portfolio_data(
            file, user_id=str(current_user.id)
        )

        # Construct a Portfolio Pydantic model instance from the parsed data.
        # This instance is not saved to the database here.
        # It won't have a database ID, created_at, or updated_at yet.
        # The Portfolio model should handle default values for fields not in parsed_data_dict.

        # Ensure user_id is of the correct type if Portfolio model expects PydanticObjectId
        # The parsed_data_dict from the service already excludes user_id, id, created_at, updated_at
        portfolio_to_return = Portfolio(
            user_id=current_user.id,  # This should be PydanticObjectId from current_user
            **(parsed_data_dict or {}),
        )

        # Set default timestamps if needed for the response model, though typically these are DB-generated.
        # For a non-persisted object, they might be None or set to now.
        # The Portfolio model's default_factory for created_at/updated_at will handle this if they are defined with it.
        # If not, and they are required in the response, we might need to set them.
        # However, for a non-saved entity, these fields having values could be misleading.
        # Let's assume the Portfolio model handles their defaults (e.g. to None or a default time if appropriate).

        logger.info(
            f"Successfully parsed document for user {current_user.id}. Returning structured data."
        )
        return portfolio_to_return

    except ValueError as ve:
        logger.error(
            f"Value error during portfolio document parsing for user {current_user.id}: {ve}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process document: {ve}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in parse_portfolio_document for user {current_user.id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred processing the document: {str(e)}",
        )
    finally:
        if file:  # Ensure file is closed if it was opened
            await file.close()
