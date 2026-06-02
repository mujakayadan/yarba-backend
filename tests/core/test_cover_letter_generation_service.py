"""Tests for the cover letter generation service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from core.services.cover_letter_generation_service import CoverLetterGenerationService


@pytest.fixture
def generation_service():
    return CoverLetterGenerationService(
        cover_letter_repository=AsyncMock(),
        portfolio_repository=AsyncMock(),
        profile_repository=AsyncMock(),
        resume_repository=AsyncMock(),
        llm_service=AsyncMock(),
        prompt_service=AsyncMock(),
        latex_service=AsyncMock(),
    )


def _cover_letter_mock(**kwargs):
    cover_letter = MagicMock()
    cover_letter.id = kwargs.get("id", PydanticObjectId())
    cover_letter.user_id = kwargs.get("user_id", PydanticObjectId())
    cover_letter.profile_id = kwargs.get("profile_id", PydanticObjectId())
    cover_letter.portfolio_id = kwargs.get("portfolio_id", PydanticObjectId())
    cover_letter.resume_id = kwargs.get("resume_id", PydanticObjectId())
    cover_letter.content = kwargs.get("content", "Dear hiring manager,")
    cover_letter.save = AsyncMock()
    return cover_letter


@pytest.mark.asyncio
async def test_get_cover_letter_data_success(generation_service):
    cover_letter = _cover_letter_mock()
    profile = MagicMock()
    portfolio = MagicMock()
    resume = MagicMock()

    generation_service.cover_letter_repository.get_by_id = AsyncMock(
        return_value=cover_letter
    )
    generation_service.profile_repository.get_by_id = AsyncMock(return_value=profile)
    generation_service.portfolio_repository.get_by_id = AsyncMock(
        return_value=portfolio
    )
    generation_service.resume_repository.get_by_id = AsyncMock(return_value=resume)

    result = await generation_service.get_cover_letter_data(cover_letter.id)
    assert result[0] == cover_letter
    assert result[1] == profile
    assert result[2] == portfolio
    assert result[3] == resume


@pytest.mark.asyncio
async def test_generate_cover_letter_content_persists_llm_output(generation_service):
    cover_letter = _cover_letter_mock(content=None)
    profile = MagicMock(personal_information=MagicMock(full_name="Test User"))
    profile.life_story = None
    portfolio = MagicMock()
    resume = MagicMock(
        job_title="Engineer",
        company_name="Acme",
        job_description="Backend role",
        content={"summary": "Developer"},
    )

    generation_service.get_cover_letter_data = AsyncMock(
        return_value=(cover_letter, profile, portfolio, resume)
    )
    generation_service.configure_for_user = AsyncMock()
    generation_service.prompt_service.get_cover_letter_prompt = AsyncMock(
        return_value="Write a cover letter"
    )
    generation_service.prompt_service.get_system_prompt = AsyncMock(
        return_value="You are helpful"
    )
    generation_service.llm_service.get_completion = AsyncMock(
        return_value={"llm_output": '{"full_document": "Dear hiring manager,"}'}
    )

    result = await generation_service.generate_cover_letter_content(
        cover_letter_id=cover_letter.id,
        regenerate=True,
    )

    assert "Dear hiring manager" in result
    generation_service.llm_service.get_completion.assert_awaited_once()
    cover_letter.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_pdf_skips_content_generation_when_present(
    generation_service, monkeypatch
):
    cover_letter = _cover_letter_mock(content="Already written")
    profile = MagicMock()
    portfolio = MagicMock()
    resume = MagicMock(company_name="Acme", job_title="Engineer")

    generation_service.get_cover_letter_data = AsyncMock(
        return_value=(cover_letter, profile, portfolio, resume)
    )
    generation_service.generate_cover_letter_content = AsyncMock()
    generation_service.generate_latex = AsyncMock(
        return_value="\\documentclass{article}"
    )
    generation_service.latex_service.compile_latex_to_pdf = AsyncMock(
        return_value=b"%PDF-1.4"
    )

    storage = AsyncMock(
        save_cover_letter_pdf=AsyncMock(return_value="cover-letters/key.pdf")
    )
    monkeypatch.setattr(
        "utils.storage.get_storage_provider",
        lambda: storage,
    )
    pdf_bytes = await generation_service.generate_pdf(cover_letter.id)

    assert pdf_bytes == b"%PDF-1.4"
    generation_service.generate_cover_letter_content.assert_not_awaited()
