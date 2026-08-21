"""Typed, service-owned content-policy classification."""

import re
from dataclasses import dataclass
from enum import StrEnum

import litellm

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    REJECT = "reject"
    UNDER_REVIEW = "under_review"


@dataclass(frozen=True, slots=True)
class PolicyResult:
    decision: PolicyDecision
    categories: tuple[str, ...] = ()
    provider: str = "local"


_ILLEGAL_PATTERNS = (
    re.compile(r"\b(?:sell|buy)\s+(?:illegal\s+)?(?:drugs|stolen credentials)\b", re.I),
    re.compile(r"\b(?:phishing kit|child sexual abuse material|csam)\b", re.I),
)
_SEXUAL_PATTERNS = (
    re.compile(r"\b(?:pornography|sexually explicit|sexual services)\b", re.I),
    re.compile(r"\b(?:nude|intimate)\s+(?:photo|image|video)s?\b", re.I),
)


class ContentPolicyService:
    """Classify relevant content without consulting user-supplied provider keys."""

    async def review_text(self, text: str, *, publication: bool) -> PolicyResult:
        local = self._local_review(text)
        if local.decision == PolicyDecision.REJECT:
            return local
        if not text.strip():
            return PolicyResult(PolicyDecision.ALLOW)
        if not settings.llm.openai_api_key:
            return PolicyResult(
                PolicyDecision.UNDER_REVIEW if publication else PolicyDecision.ALLOW,
                ("provider_unavailable",),
            )
        try:
            response = await litellm.amoderation(
                model=settings.llm.moderation_model,
                input=text,
                api_key=settings.llm.openai_api_key,
            )
            result = response.results[0]
            if not result.flagged:
                return PolicyResult(PolicyDecision.ALLOW, provider="openai")
            categories = tuple(
                name
                for name, flagged in result.categories.model_dump().items()
                if flagged
            )
            prohibited = tuple(
                name for name in categories if name.startswith(("sexual", "illicit"))
            )
            if prohibited:
                return PolicyResult(
                    PolicyDecision.REJECT, prohibited, provider="openai"
                )
            return PolicyResult(
                PolicyDecision.UNDER_REVIEW, categories, provider="openai"
            )
        except Exception:
            logger.exception("Service-owned content moderation failed")
            return PolicyResult(
                PolicyDecision.UNDER_REVIEW if publication else PolicyDecision.ALLOW,
                ("provider_error",),
            )

    def _local_review(self, text: str) -> PolicyResult:
        categories: list[str] = []
        if any(pattern.search(text) for pattern in _ILLEGAL_PATTERNS):
            categories.append("illegal_content")
        if any(pattern.search(text) for pattern in _SEXUAL_PATTERNS):
            categories.append("sexual_content")
        if categories:
            return PolicyResult(PolicyDecision.REJECT, tuple(categories))
        return PolicyResult(PolicyDecision.ALLOW)
