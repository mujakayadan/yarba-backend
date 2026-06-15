"""Tests for resume generation service."""

from unittest.mock import AsyncMock

import pytest
from beanie import PydanticObjectId

from core.services.resume_generation_service import ResumeGenerationService
from tests.factories import make_portfolio, make_profile, make_resume


@pytest.fixture
def generation_service():
    return ResumeGenerationService(
        resume_repository=AsyncMock(),
        portfolio_repository=AsyncMock(),
        profile_repository=AsyncMock(),
        prompt_service=AsyncMock(),
        profile_service=AsyncMock(),
        portfolio_service=AsyncMock(),
        llm_service=AsyncMock(),
        latex_service=AsyncMock(),
        job_service=AsyncMock(),
    )


def test_generation_service_init(generation_service):
    assert generation_service.resume_repository is not None
    assert generation_service.llm_service is not None


def test_generate_proper_title():
    from core.utils.resume_title import generate_resume_title

    title = generate_resume_title("acme_corp", "backend_engineer")
    assert "Acme Corp" in title
    assert "Backend Engineer" in title


@pytest.mark.asyncio
async def test_get_resume_data_raises_when_resume_missing(generation_service):
    generation_service.resume_repository.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="Resume with ID"):
        await generation_service.get_resume_data(PydanticObjectId())


@pytest.mark.asyncio
async def test_get_resume_data_success(generation_service):
    user_id = PydanticObjectId()
    profile_id = PydanticObjectId()
    portfolio_id = PydanticObjectId()
    profile = make_profile(user_id=user_id)
    profile.id = profile_id
    portfolio = make_portfolio(user_id=user_id, profile_id=profile_id)
    portfolio.id = portfolio_id
    resume = make_resume(
        user_id=user_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
    )

    generation_service.resume_repository.get_by_id = AsyncMock(return_value=resume)
    generation_service.profile_repository.get_by_id = AsyncMock(return_value=profile)
    generation_service.portfolio_service.get_portfolio_by_id = AsyncMock(
        return_value=portfolio
    )

    result = await generation_service.get_resume_data(resume.id)
    assert result[0] == resume
    assert result[1] == profile
    assert result[2] == portfolio
