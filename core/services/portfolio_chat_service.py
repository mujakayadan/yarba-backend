"""Service for portfolio website chatbot."""

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from api.schemas.portfolio_chat import (
    MAX_CHAT_HISTORY,
    ChatMessage,
    PortfolioChatRequest,
    PortfolioChatResponse,
)
from config.logging_config import get_logger
from core.exceptions.base import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from core.models.portfolio import Portfolio
from core.models.portfolio_chat_conversation import PortfolioChatVisitorMetadata
from core.models.profile import Profile
from core.repositories.portfolio_chat_conversation_repository import (
    PortfolioChatConversationRepository,
)
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.portfolio_website_repository import PortfolioWebsiteRepository
from core.repositories.profile_repository import ProfileRepository
from core.services.llm_service import LLMService
from core.utils.object_id import require_object_id
from prompts.portfolio_chat_prompts import PortfolioChatSystemPrompt

_SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
_TRAILING_URL_PUNCTUATION = ".,;:!?)]}\"'"
_SCHEDULING_KEYWORDS = (
    "calendly",
    "schedule",
    "appointment",
    "book a call",
    "book a meeting",
    "meeting link",
)


@dataclass(frozen=True)
class ChatVisitorMetadata:
    """Optional request metadata from the public chat widget."""

    user_agent: str | None = None
    referrer: str | None = None


class PortfolioChatService:
    """Handle chat requests for published portfolio websites."""

    def __init__(
        self,
        website_repository: PortfolioWebsiteRepository,
        portfolio_repository: PortfolioRepository,
        profile_repository: ProfileRepository,
        conversation_repository: PortfolioChatConversationRepository,
        llm_service: LLMService,
    ) -> None:
        self.website_repository = website_repository
        self.portfolio_repository = portfolio_repository
        self.profile_repository = profile_repository
        self.conversation_repository = conversation_repository
        self.llm_service = llm_service
        self.logger = get_logger(self.__class__.__name__)

    async def chat(
        self,
        request: PortfolioChatRequest,
        visitor_metadata: ChatVisitorMetadata | None = None,
    ) -> PortfolioChatResponse:
        """Process a chat message for a portfolio subdomain."""
        subdomain = request.subdomain.strip().lower()
        self._validate_subdomain(subdomain)

        website = await self.website_repository.get_by_subdomain(subdomain)
        if not website or not website.is_published:
            raise NotFoundException(message="Portfolio website not found")

        if not website.config.chatbot_enabled:
            raise ForbiddenException(message="Chatbot is not enabled for this website")

        portfolio = await self.portfolio_repository.get_by_id(website.portfolio_id)
        if not portfolio:
            raise NotFoundException(message="Portfolio not found")

        profile = await self.profile_repository.get_by_user_id(website.user_id)
        system_prompt = self._build_system_prompt(portfolio, profile)

        conversation_id = request.conversation_id or str(uuid.uuid4())
        store_conversations = website.config.chatbot_store_conversations
        history = await self._resolve_history(
            request=request,
            conversation_id=conversation_id,
            store_conversations=store_conversations,
            website_user_id=website.user_id,
        )
        messages = self._build_messages(system_prompt, history, request.message)

        result = await self.llm_service.get_chat_completion(
            messages=messages,
            user_id=str(website.user_id),
            tags=["operation:portfolio_chat"],
            temperature=0.7,
        )
        assistant_response = result["llm_output"]

        if store_conversations:
            calendly_url = (
                profile.personal_information.calendly_url if profile else None
            )
            await self.conversation_repository.append_exchange(
                conversation_id=conversation_id,
                user_id=website.user_id,
                website_id=require_object_id(website.id),
                portfolio_id=website.portfolio_id,
                subdomain=subdomain,
                user_message=request.message,
                assistant_message=assistant_response,
                visitor_metadata=self._to_visitor_metadata(visitor_metadata),
                calendly_mentioned=self._mentions_scheduling(
                    assistant_response, calendly_url
                ),
            )

        return PortfolioChatResponse(
            response=assistant_response,
            conversation_id=conversation_id,
        )

    async def _resolve_history(
        self,
        *,
        request: PortfolioChatRequest,
        conversation_id: str,
        store_conversations: bool,
        website_user_id: Any,
    ) -> list[ChatMessage]:
        if store_conversations and request.conversation_id:
            stored = await self.conversation_repository.get_by_conversation_id(
                conversation_id
            )
            if stored and stored.user_id == website_user_id:
                return [
                    ChatMessage(role=message.role, content=message.content)
                    for message in stored.messages[-MAX_CHAT_HISTORY:]
                ]

        return request.history[-MAX_CHAT_HISTORY:]

    def _validate_subdomain(self, subdomain: str) -> None:
        if not _SUBDOMAIN_PATTERN.match(subdomain) or "--" in subdomain:
            raise BadRequestException(message="Invalid subdomain format")

    def _build_messages(
        self,
        system_prompt: str,
        history: list[ChatMessage],
        message: str,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for item in history:
            messages.append({"role": item.role, "content": item.content})
        messages.append({"role": "user", "content": message})
        return messages

    def _build_system_prompt(
        self, portfolio: Portfolio, profile: Profile | None
    ) -> str:
        personal = profile.personal_information if profile else None
        full_name = (
            personal.full_name
            if personal and personal.full_name
            else "the portfolio owner"
        )
        contact_email = str(personal.email) if personal and personal.email else None
        calendly_url = personal.calendly_url if personal else None
        life_story = profile.life_story if profile else None

        knowledge = self._serialize_portfolio_knowledge(portfolio, life_story)
        prompt = PortfolioChatSystemPrompt()
        return prompt.format(
            full_name=full_name,
            contact_email=contact_email,
            calendly_url=calendly_url,
            portfolio_knowledge=knowledge,
        )

    def _serialize_portfolio_knowledge(
        self,
        portfolio: Portfolio,
        life_story: str | None,
    ) -> str:
        sections: dict[str, Any] = {}

        if portfolio.career_summary:
            sections["career_summary"] = portfolio.career_summary.model_dump()
        if portfolio.work_experience:
            sections["work_experience"] = [
                exp.model_dump() for exp in portfolio.work_experience
            ]
        if portfolio.education:
            sections["education"] = [edu.model_dump() for edu in portfolio.education]
        if portfolio.skills:
            sections["skills"] = [skill.model_dump() for skill in portfolio.skills]
        if portfolio.projects:
            sections["projects"] = [
                {**proj.model_dump(), "link": str(proj.link) if proj.link else None}
                for proj in portfolio.projects
            ]
        if portfolio.awards:
            sections["awards"] = [award.model_dump() for award in portfolio.awards]
        if portfolio.publications:
            sections["publications"] = [
                pub.model_dump() for pub in portfolio.publications
            ]
        if portfolio.certifications:
            sections["certifications"] = portfolio.certifications
        if portfolio.custom_sections:
            sections["custom_sections"] = portfolio.custom_sections.model_dump()
        if life_story:
            sections["life_story"] = life_story

        return json.dumps(sections, indent=2, default=str)

    @staticmethod
    def _to_visitor_metadata(
        metadata: ChatVisitorMetadata | None,
    ) -> PortfolioChatVisitorMetadata | None:
        if metadata is None:
            return None
        if not metadata.user_agent and not metadata.referrer:
            return None
        return PortfolioChatVisitorMetadata(
            user_agent=metadata.user_agent,
            referrer=metadata.referrer,
        )

    @staticmethod
    def _normalized_response_urls(response: str) -> set[str]:
        urls: set[str] = set()
        for match in _URL_PATTERN.finditer(response):
            candidate = match.group(0).rstrip(_TRAILING_URL_PUNCTUATION)
            try:
                if urlparse(candidate).hostname:
                    urls.add(candidate.rstrip("/").lower())
            except ValueError:
                continue
        return urls

    @staticmethod
    def _mentions_scheduling(assistant_response: str, calendly_url: str | None) -> bool:
        lowered = assistant_response.lower()
        if calendly_url:
            normalized = calendly_url.lower().rstrip("/")
            response_urls = PortfolioChatService._normalized_response_urls(
                assistant_response
            )
            if normalized in response_urls:
                return True
        return any(keyword in lowered for keyword in _SCHEDULING_KEYWORDS)
