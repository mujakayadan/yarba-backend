"""Portfolio router for the API."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

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
from core.models.user import User
from core.repositories.portfolio_repository import PortfolioRepository

from ..dependencies.auth import get_current_active_user

router = APIRouter()


class PortfolioCreate(BaseModel):
    """Portfolio creation model."""

    profile_id: Optional[str] = None


class PortfolioUpdate(BaseModel):
    """Portfolio update model."""

    profile_id: Optional[str] = None
    professional_title: Optional[str] = None
    career_summary: Optional[CareerSummary] = None
    skills: Optional[List[Skill]] = None
    work_experience: Optional[List[WorkExperience]] = None
    education: Optional[List[Education]] = None
    projects: Optional[List[Project]] = None
    awards: Optional[List[Award]] = None
    publications: Optional[List[Publication]] = None
    certifications: Optional[List[str]] = None
    custom_sections: Optional[CustomSections] = None
    is_active: Optional[bool] = None
    version: Optional[str] = None


class PortfolioItemCreate(BaseModel):
    """Schema for creating a portfolio item."""

    type: str
    url: Optional[str] = None
    bullet_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date: Optional[str] = None
    order: Optional[int] = None
    is_featured: Optional[bool] = False

    # Work experience fields
    company: Optional[str] = None
    location: Optional[str] = None


class PortfolioItemUpdate(BaseModel):
    """Schema for updating a portfolio item."""

    type: Optional[str] = None
    url: Optional[str] = None
    bullet_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date: Optional[str] = None
    order: Optional[int] = None
    is_featured: Optional[bool] = None

    # Work experience fields
    company: Optional[str] = None
    location: Optional[str] = None


class PortfolioPatchOperation(BaseModel):
    """Schema for a portfolio patch operation."""

    # Optional fields that can be individually updated
    career_summary: Optional[CareerSummary] = None
    skills: Optional[List[Skill]] = None
    work_experience: Optional[List[WorkExperience]] = None
    education: Optional[List[Education]] = None
    projects: Optional[List[Project]] = None
    awards: Optional[List[Award]] = None
    publications: Optional[List[Publication]] = None
    certifications: Optional[List[str]] = None
    custom_sections: Optional[CustomSections] = None
    is_active: Optional[bool] = None
    version: Optional[str] = None
    profile_id: Optional[str] = None
    professional_title: Optional[str] = None


@router.get("/", response_model=Portfolio)
async def get_portfolios(
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Get the portfolio for the current user.

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
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Create a new portfolio.

    Args:
        portfolio_data: Portfolio data
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Created portfolio
    """
    # Create career summary if provided
    career_summary = None
    if portfolio_data.career_summary:
        career_summary = CareerSummary(**portfolio_data.career_summary)

    # Create portfolio
    portfolio = Portfolio(
        user_id=current_user.id,
        title=portfolio_data.title,
        description=portfolio_data.description,
        professional_title=portfolio_data.professional_title,
        career_summary=career_summary,
        theme=portfolio_data.theme,
        layout=portfolio_data.layout,
        items_per_page=portfolio_data.items_per_page,
        is_public=portfolio_data.is_public,
    )

    await portfolio.create()
    return portfolio


@router.get("/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Get a portfolio by ID.

    Args:
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update a portfolio.

    Args:
        portfolio_data: Portfolio data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
        portfolio.career_summary = CareerSummary(**portfolio_data.career_summary)

    # Update portfolio fields
    for field, value in portfolio_data.dict(exclude_unset=True).items():
        if field != "career_summary":  # Skip career summary as it's handled above
            setattr(portfolio, field, value)

    await portfolio.save()
    return portfolio


@router.patch("/{portfolio_id}", response_model=Portfolio)
async def patch_portfolio(
    portfolio_data: PortfolioPatchOperation,
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Partially update a portfolio (only specified fields).

    Args:
        portfolio_data: Portfolio data to patch
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    patch_data = portfolio_data.dict(exclude_unset=True)

    # Handle special case for career_summary which needs to be instantiated as a model
    if "career_summary" in patch_data:
        portfolio.career_summary = CareerSummary(**patch_data.pop("career_summary"))

    # Update remaining portfolio fields
    for field, value in patch_data.items():
        setattr(portfolio, field, value)

    # Update the timestamp
    portfolio.updated_at = datetime.now(timezone.utc)

    await portfolio.save()
    return portfolio


@router.patch("/{portfolio_id}/career-summary", response_model=Portfolio)
async def patch_career_summary(
    career_summary: CareerSummary,
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update only the career summary section of a portfolio.

    Args:
        career_summary: Career summary data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    await portfolio_repository.update_career_summary(portfolio.id, career_summary)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(portfolio_id)


@router.patch("/{portfolio_id}/skills", response_model=Portfolio)
async def patch_skills(
    skills: List[Skill],
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update only the skills section of a portfolio.

    Args:
        skills: Skills data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    await portfolio_repository.update_skills(portfolio.id, skills)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(portfolio_id)


@router.patch("/{portfolio_id}/work-experience", response_model=Portfolio)
async def patch_work_experience(
    work_experience: List[WorkExperience],
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update only the work experience section of a portfolio.

    Args:
        work_experience: Work experience data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    await portfolio_repository.update_work_experience(portfolio.id, work_experience)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(portfolio_id)


@router.patch("/{portfolio_id}/education", response_model=Portfolio)
async def patch_education(
    education: List[Education],
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update only the education section of a portfolio.

    Args:
        education: Education data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    await portfolio_repository.update_education(portfolio.id, education)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(portfolio_id)


@router.patch("/{portfolio_id}/projects", response_model=Portfolio)
async def patch_projects(
    projects: List[Project],
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update only the projects section of a portfolio.

    Args:
        projects: Projects data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    await portfolio_repository.update_projects(portfolio.id, projects)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(portfolio_id)


@router.patch("/{portfolio_id}/awards", response_model=Portfolio)
async def patch_awards(
    awards: List[Award],
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update only the awards section of a portfolio.

    Args:
        awards: Awards data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    await portfolio_repository.update_awards(portfolio.id, awards)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(portfolio_id)


@router.patch("/{portfolio_id}/publications", response_model=Portfolio)
async def patch_publications(
    publications: List[Publication],
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update only the publications section of a portfolio.

    Args:
        publications: Publications data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
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
    await portfolio_repository.update_publications(portfolio.id, publications)

    # Return updated portfolio
    return await portfolio_repository.get_by_id(portfolio_id)


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    uow: AsyncMongoUnitOfWork = Depends(get_unit_of_work),
):
    """
    Delete a portfolio.

    Args:
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        uow: Unit of work

    Returns:
        None
    """
    async with uow:
        portfolio = await uow.portfolio_repository.get_by_id(portfolio_id)
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

        # Delete all portfolio items
        portfolio_items = await uow.portfolio_repository.get_items(portfolio)
        for item in portfolio_items:
            await item.delete()

        # Delete the portfolio
        await portfolio.delete()


@router.delete(
    "/{portfolio_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_portfolio_item(
    portfolio_id: str = Path(..., description="Portfolio ID"),
    item_id: str = Path(..., description="Portfolio item ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Delete a portfolio item.

    Args:
        portfolio_id: Portfolio ID
        item_id: Portfolio item ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        None
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user
    if portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete items from this portfolio",
        )

    # Get portfolio item
    item = await portfolio_repository.get_item_by_id(item_id)
    if not item or item.portfolio_id != portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found",
        )

    # Delete the portfolio item
    await item.delete()


@router.get("/by-profile/{profile_id}", response_model=Portfolio)
async def get_portfolio_by_profile(
    profile_id: str = Path(..., description="Profile ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Get a portfolio by profile ID.

    Args:
        profile_id: Profile ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Portfolio
    """
    portfolio = await portfolio_repository.get_by_profile_id(profile_id)
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
