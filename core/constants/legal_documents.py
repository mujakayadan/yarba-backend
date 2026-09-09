"""Approved Yarba legal-document seed content.

Canonical displayed copy lives in yarba-frontend `src/content/legalDocuments.ts`.
When that copy changes, regenerate `legal_documents.json` from
`formatLegalDocumentContent()` and bump LEGAL_VERSION so existing acceptances
re-gate.
"""

import json
from pathlib import Path

LEGAL_VERSION = "2026-09-09"
_SEED_PATH = Path(__file__).with_name("legal_documents.json")


def _load_approved_documents() -> dict[str, tuple[str, str]]:
    payload = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
    return {
        document_type: (item["title"], item["content"])
        for document_type, item in payload.items()
    }


APPROVED_LEGAL_DOCUMENTS = _load_approved_documents()
