"""Seeded legal documents must match the published frontend policy text."""

from core.constants.legal_documents import APPROVED_LEGAL_DOCUMENTS, LEGAL_VERSION


def test_seeded_legal_documents_use_full_published_policy_text() -> None:
    terms_title, terms = APPROVED_LEGAL_DOCUMENTS["terms"]

    assert LEGAL_VERSION == "2026-09-09"
    assert terms_title == "Terms of Service"
    assert "6. Public portfolio websites" in terms
    assert "yarba.app subdomain" in terms
    assert len(terms) > 2000
    assert all(
        document_type in APPROVED_LEGAL_DOCUMENTS
        for document_type in (
            "terms",
            "privacy",
            "acceptable_use",
            "copyright_dmca",
            "ai_data_use",
            "site_visitor_privacy",
        )
    )
