"""Portfolio router for the API."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from core.database import get_portfolio_repository, get_unit_of_work
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.models.portfolio import CareerSummary, Portfolio, PortfolioItem
from core.models.user import User
from core.repositories.portfolio import PortfolioRepository

from ..dependencies.auth import get_current_active_user

router = APIRouter()


class PortfolioCreate(BaseModel):
    """Schema for creating a portfolio."""

    title: str
    description: Optional[str] = None
    professional_title: Optional[str] = None
    career_summary: Optional[dict] = None
    theme: Optional[str] = "modern"
    layout: Optional[str] = "grid"
    items_per_page: Optional[int] = 10
    is_public: Optional[bool] = False


class PortfolioUpdate(BaseModel):
    """Schema for updating a portfolio."""

    title: Optional[str] = None
    description: Optional[str] = None
    professional_title: Optional[str] = None
    career_summary: Optional[dict] = None
    theme: Optional[str] = None
    layout: Optional[str] = None
    items_per_page: Optional[int] = None
    is_public: Optional[bool] = None


class PortfolioItemCreate(BaseModel):
    """Schema for creating a portfolio item."""

    title: str
    description: Optional[str] = None
    type: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    technologies: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date: Optional[str] = None
    highlights: Optional[List[str]] = None
    order: Optional[int] = None
    is_featured: Optional[bool] = False
    metadata: Optional[dict] = None

    # Work experience fields
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Education fields
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    gpa: Optional[str] = None
    courses: Optional[List[str]] = None

    # Publication fields
    authors: Optional[List[str]] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None

    # Award fields
    issuer: Optional[str] = None
    issue_date: Optional[str] = None


class PortfolioItemUpdate(BaseModel):
    """Schema for updating a portfolio item."""

    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    technologies: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    date: Optional[str] = None
    highlights: Optional[List[str]] = None
    order: Optional[int] = None
    is_featured: Optional[bool] = None
    metadata: Optional[dict] = None

    # Work experience fields
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Education fields
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    gpa: Optional[str] = None
    courses: Optional[List[str]] = None

    # Publication fields
    authors: Optional[List[str]] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None

    # Award fields
    issuer: Optional[str] = None
    issue_date: Optional[str] = None


@router.get("/", response_model=List[Portfolio])
async def get_portfolios(
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Get all portfolios for the current user.

    Args:
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        List of portfolios
    """
    return await portfolio_repository.get_by_user(current_user)


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


@router.get("/{portfolio_id}/items", response_model=List[PortfolioItem])
async def get_portfolio_items(
    portfolio_id: str = Path(..., description="Portfolio ID"),
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Get all items for a portfolio.

    Args:
        portfolio_id: Portfolio ID
        item_type: Filter by item type
        tag: Filter by tag
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        List of portfolio items
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user or is public
    if portfolio.user_id != current_user.id and not portfolio.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio",
        )

    # Get portfolio items
    if item_type:
        items = await portfolio_repository.get_items_by_type(portfolio, item_type)
    elif tag:
        items = await portfolio_repository.get_items_by_tag(portfolio, tag)
    else:
        items = await portfolio_repository.get_items(portfolio)

    return items


@router.post(
    "/{portfolio_id}/items",
    response_model=PortfolioItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio_item(
    item_data: PortfolioItemCreate,
    portfolio_id: str = Path(..., description="Portfolio ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Create a new portfolio item.

    Args:
        item_data: Portfolio item data
        portfolio_id: Portfolio ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Created portfolio item
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
            detail="Not authorized to add items to this portfolio",
        )

    # Create portfolio item
    item = PortfolioItem(
        portfolio_id=portfolio_id,
        **item_data.dict(),
    )

    await item.create()
    return item


@router.get("/{portfolio_id}/items/{item_id}", response_model=PortfolioItem)
async def get_portfolio_item(
    portfolio_id: str = Path(..., description="Portfolio ID"),
    item_id: str = Path(..., description="Portfolio item ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Get a portfolio item by ID.

    Args:
        portfolio_id: Portfolio ID
        item_id: Portfolio item ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Portfolio item
    """
    portfolio = await portfolio_repository.get_by_id(portfolio_id)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    # Check if the portfolio belongs to the current user or is public
    if portfolio.user_id != current_user.id and not portfolio.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this portfolio",
        )

    # Get portfolio item
    item = await portfolio_repository.get_item_by_id(item_id)
    if not item or item.portfolio_id != portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found",
        )

    return item


@router.put("/{portfolio_id}/items/{item_id}", response_model=PortfolioItem)
async def update_portfolio_item(
    item_data: PortfolioItemUpdate,
    portfolio_id: str = Path(..., description="Portfolio ID"),
    item_id: str = Path(..., description="Portfolio item ID"),
    current_user: User = Depends(get_current_active_user),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository),
):
    """
    Update a portfolio item.

    Args:
        item_data: Portfolio item data
        portfolio_id: Portfolio ID
        item_id: Portfolio item ID
        current_user: Current authenticated user
        portfolio_repository: Portfolio repository

    Returns:
        Updated portfolio item
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
            detail="Not authorized to update items in this portfolio",
        )

    # Get portfolio item
    item = await portfolio_repository.get_item_by_id(item_id)
    if not item or item.portfolio_id != portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found",
        )

    # Update portfolio item fields
    for field, value in item_data.dict(exclude_unset=True).items():
        setattr(item, field, value)

    await item.save()
    return item


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
