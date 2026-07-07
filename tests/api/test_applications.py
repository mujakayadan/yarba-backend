"""Tests for application profile and logging APIs."""

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from config.settings import settings
from core.models.profile import Profile
from core.schemas.application_preferences import DemographicConsent
from tests.factories import make_resume


def _jwt_for_user(user) -> str:
    return jwt.encode(
        {"sub": user.email},
        settings.auth.jwt_secret_key.get_secret_value(),
        algorithm=settings.auth.jwt_algorithm,
    )


@pytest.mark.asyncio
async def test_application_profile_uses_profile_contact_not_resume_llm(
    beanie_db, async_client: AsyncClient, test_user, test_profile, test_portfolio
):
    profile = test_profile
    profile.personal_information.full_name = "Profile Name"
    profile.personal_information.email = "profile@example.com"
    await profile.save()

    resume = make_resume(
        user_id=test_user.id,
        profile_id=test_profile.id,
        portfolio_id=test_portfolio.id,
        content={
            "personal_information": {
                "full_name": "LLM Wrong Name",
                "email": "wrong@example.com",
            }
        },
    )
    await resume.insert()

    resp = await async_client.get(
        "/api/v1/applications/profile",
        params={"resume_id": str(resume.id)},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["contact"]["full_name"] == "Profile Name"
    assert data["contact"]["email"] == "profile@example.com"


@pytest.mark.asyncio
async def test_demographics_require_consent(
    beanie_db, async_client: AsyncClient, test_user
):
    token = _jwt_for_user(test_user)
    resp = await async_client.put(
        "/api/v1/profiles/me/application-preferences/demographics",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "gender": "male",
            "race_ethnicity": [],
            "veteran_status": "not_a_veteran",
            "disability_status": "no",
        },
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_demographics_stored_encrypted(
    beanie_db, async_client: AsyncClient, test_user, test_profile
):
    profile = test_profile
    profile.application_preferences.demographic_consent = DemographicConsent(
        consented=True
    )
    await profile.save()

    token = _jwt_for_user(test_user)
    payload = {
        "gender": "female",
        "race_ethnicity": ["asian"],
        "veteran_status": "not_a_veteran",
        "disability_status": "no",
    }
    resp = await async_client.put(
        "/api/v1/profiles/me/application-preferences/demographics",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp.status_code == status.HTTP_200_OK

    refreshed = await Profile.get(test_profile.id)
    assert refreshed is not None
    assert refreshed.demographics_encrypted is not None
    assert "female" not in refreshed.demographics_encrypted


@pytest.mark.asyncio
async def test_apply_credentials_stored_encrypted(
    beanie_db, async_client: AsyncClient, test_user, test_profile
):
    token = _jwt_for_user(test_user)
    resp = await async_client.put(
        "/api/v1/profiles/me/application-preferences/apply-credentials",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "CareersSitePass1!"},
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    refreshed = await Profile.get(test_profile.id)
    assert refreshed is not None
    assert refreshed.apply_credentials_encrypted is not None
    assert "CareersSitePass1" not in refreshed.apply_credentials_encrypted

    status_resp = await async_client.get(
        "/api/v1/profiles/me/application-preferences/apply-credentials",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.json() == {"configured": True}


@pytest.mark.asyncio
async def test_apply_credentials_in_profile_for_jwt(
    beanie_db, async_client: AsyncClient, test_user, test_profile, test_portfolio
):
    token = _jwt_for_user(test_user)
    await async_client.put(
        "/api/v1/profiles/me/application-preferences/apply-credentials",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "CareersSitePass1!"},
    )

    resume = make_resume(
        user_id=test_user.id,
        profile_id=test_profile.id,
        portfolio_id=test_portfolio.id,
    )
    await resume.insert()

    resp = await async_client.get(
        "/api/v1/applications/profile",
        params={"resume_id": str(resume.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["apply_account_password"] == "CareersSitePass1!"


@pytest.mark.asyncio
async def test_create_application_log(
    beanie_db, async_client: AsyncClient, test_resume
):
    resp = await async_client.post(
        "/api/v1/applications",
        json={
            "job_url": "https://boards.greenhouse.io/example/jobs/1",
            "company_name": "Example Co",
            "job_title": "Engineer",
            "resume_id": str(test_resume.id),
            "status": "draft",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    body = resp.json()
    assert body["status"] == "draft"
    assert body["platform"] == "boards.greenhouse.io"
