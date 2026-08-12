"""Tests for public portfolio content API."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from core.models.portfolio import Portfolio, WorkExperience
from core.models.portfolio_site_token import PortfolioSiteToken
from core.utils.portfolio_site_token import generate_raw_token, hash_token

CONTENT_URL = "/api/v1/public/portfolio/content"
TOKEN_HEADER = "X-Portfolio-Site-Token"


@pytest.fixture
async def portfolio_site_token(test_user, test_portfolio, beanie_db):
    raw_token = generate_raw_token()
    now = datetime.now(UTC)
    record = PortfolioSiteToken(
        token_hash=hash_token(raw_token),
        user_id=test_user.id,
        portfolio_id=test_portfolio.id,
        label="test-site",
        scopes=["portfolio:read"],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    await record.insert()
    return raw_token


@pytest.mark.anyio
async def test_public_portfolio_content_success(
    async_client: AsyncClient,
    portfolio_site_token: str,
    test_profile,
    test_portfolio,
):
    test_portfolio.work_experience = [
        WorkExperience(
            job_title="Older role",
            start_date="2019-01",
            end_date="2020-01",
        ),
        WorkExperience(
            job_title="Newer role",
            start_date="2024-01",
            end_date="2025-01",
        ),
    ]
    await test_portfolio.save()

    response = await async_client.get(
        CONTENT_URL,
        headers={TOKEN_HEADER: portfolio_site_token},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["personal"]["full_name"] == test_profile.personal_information.full_name
    assert "career_summary" in body
    assert "work_experience" in body
    assert [job["job_title"] for job in body["work_experience"]] == [
        "Newer role",
        "Older role",
    ]
    assert body["work_experience"][0]["start_date"] == "2024-01"
    assert body["work_experience"][0]["end_date"] == "2025-01"
    assert body["work_experience"][0]["current"] is False
    assert "education" in body
    assert "skills" in body
    assert "projects" in body
    assert "awards" in body
    assert "publications" in body
    assert "api_keys" not in body
    assert "llm_usage" not in body


@pytest.mark.anyio
async def test_public_portfolio_content_missing_token(async_client: AsyncClient):
    response = await async_client.get(CONTENT_URL)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_public_portfolio_content_invalid_token(async_client: AsyncClient):
    response = await async_client.get(
        CONTENT_URL,
        headers={TOKEN_HEADER: "pst_invalid_token_value"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_public_portfolio_content_revoked_token(
    async_client: AsyncClient,
    portfolio_site_token: str,
    test_user,
    beanie_db,
):
    record = await PortfolioSiteToken.find_one(
        {"token_hash": hash_token(portfolio_site_token)}
    )
    assert record is not None
    record.is_active = False
    await record.save()

    response = await async_client.get(
        CONTENT_URL,
        headers={TOKEN_HEADER: portfolio_site_token},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_public_portfolio_content_no_portfolio(
    async_client: AsyncClient,
    test_user,
    beanie_db,
):
    raw_token = generate_raw_token()
    now = datetime.now(UTC)
    record = PortfolioSiteToken(
        token_hash=hash_token(raw_token),
        user_id=test_user.id,
        portfolio_id=None,
        label="no-portfolio",
        scopes=["portfolio:read"],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    await record.insert()

    await Portfolio.find(Portfolio.user_id == test_user.id).delete()

    response = await async_client.get(
        CONTENT_URL,
        headers={TOKEN_HEADER: raw_token},
    )
    assert response.status_code == 404
