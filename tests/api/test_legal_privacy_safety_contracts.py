"""Frontend-facing legal, safety, moderation, and privacy contracts."""

import pytest

from api.main import app
from api.schemas.portfolio_website import PortfolioWebsiteRequest
from api.schemas.safety import AbuseReportCategory, AbuseReportRequest
from core.services.content_policy_service import ContentPolicyService, PolicyDecision


def test_required_legal_privacy_and_safety_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/legal/acceptances/me" in paths
    assert "/api/v1/legal/acceptances" in paths
    assert "/api/v1/public/portfolio/reports" in paths
    assert "/api/v1/account/exports/latest" in paths
    assert "/api/v1/account/exports" in paths
    assert "/api/v1/account/deletion" in paths
    assert "/api/v1/admin/moderation/portfolio-websites/{website_id}/suspend" in paths


def test_abuse_report_categories_match_frontend_contract() -> None:
    assert {category.value for category in AbuseReportCategory} == {
        "illegal_content",
        "sexual_content",
        "minor_safety",
        "non_consensual_intimate_image",
        "copyright",
        "impersonation",
        "harassment",
        "privacy",
        "malware_or_phishing",
        "other",
    }
    report = AbuseReportRequest(
        subdomain="example",
        category="illegal_content",
        description="This report contains enough detail to investigate.",
    )
    assert report.reporter_email is None


def test_publication_requires_literal_rights_confirmation() -> None:
    request = PortfolioWebsiteRequest.model_validate(
        {
            "publication_acknowledgement": {
                "acceptable_use_version": "2026-08-19",
                "rights_confirmed": True,
            }
        }
    )

    assert request.publication_acknowledgement is not None
    assert request.publication_acknowledgement.rights_confirmed is True


@pytest.mark.asyncio
async def test_local_content_policy_rejects_illegal_and_explicit_content() -> None:
    service = ContentPolicyService()

    illegal = await service.review_text(
        "Buy stolen credentials from this portfolio.", publication=True
    )
    explicit = await service.review_text(
        "This site distributes sexually explicit videos.", publication=True
    )

    assert illegal.decision == PolicyDecision.REJECT
    assert "illegal_content" in illegal.categories
    assert explicit.decision == PolicyDecision.REJECT
    assert "sexual_content" in explicit.categories
