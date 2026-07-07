"""Service for public portfolio content retrieval."""

from beanie import PydanticObjectId

from api.schemas.public_portfolio import (
    PublicAward,
    PublicCareerSummary,
    PublicEducation,
    PublicPersonalInfo,
    PublicPortfolioContent,
    PublicProject,
    PublicPublication,
    PublicSkillCategory,
    PublicWorkExperience,
)
from config.settings import settings
from core.exceptions.base import NotFoundException, UnauthorizedException
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.portfolio_site_token_repository import (
    PortfolioSiteTokenRepository,
)
from core.repositories.profile_repository import ProfileRepository
from core.utils.object_id import require_object_id


class PublicPortfolioService:
    """Resolve site tokens and build sanitized portfolio payloads."""

    def __init__(
        self,
        token_repository: PortfolioSiteTokenRepository,
        portfolio_repository: PortfolioRepository,
        profile_repository: ProfileRepository,
    ) -> None:
        self.token_repository = token_repository
        self.portfolio_repository = portfolio_repository
        self.profile_repository = profile_repository

    async def get_content_by_token(self, raw_token: str) -> PublicPortfolioContent:
        """Validate token and return public portfolio content."""
        if not raw_token or not raw_token.strip():
            raise UnauthorizedException(message="Missing portfolio site token")

        token_record = await self.token_repository.get_active_by_raw_token(
            raw_token.strip()
        )
        if not token_record:
            raise UnauthorizedException(
                message="Invalid or revoked portfolio site token"
            )

        if "portfolio:read" not in token_record.scopes:
            raise UnauthorizedException(message="Token lacks portfolio:read scope")

        portfolio = await self._resolve_portfolio(
            token_record.user_id, token_record.portfolio_id
        )
        if not portfolio:
            raise NotFoundException(message="Portfolio not found for this token")

        profile = await self.profile_repository.get_by_user_id(token_record.user_id)
        await self.token_repository.touch_last_used(require_object_id(token_record.id))

        return self._build_content(portfolio, profile)

    async def _resolve_portfolio(
        self,
        user_id: PydanticObjectId,
        portfolio_id: PydanticObjectId | None,
    ) -> Portfolio | None:
        if portfolio_id:
            portfolio = await self.portfolio_repository.get_by_id(portfolio_id)
            if portfolio and portfolio.user_id == user_id:
                return portfolio
        return await self.portfolio_repository.get_by_user_id(user_id)

    def _build_profile_picture_url(self, profile: Profile | None) -> str | None:
        if not profile or not profile.profile_picture_key:
            return None
        if settings.storage.cloudfront_domain:
            return f"https://{settings.storage.cloudfront_domain}/{profile.profile_picture_key}"
        return profile.profile_picture_key

    def _build_content(
        self,
        portfolio: Portfolio,
        profile: Profile | None,
    ) -> PublicPortfolioContent:
        personal_info = profile.personal_information if profile else None
        career = portfolio.career_summary

        return PublicPortfolioContent(
            personal=PublicPersonalInfo(
                full_name=personal_info.full_name if personal_info else None,
                email=str(personal_info.email) if personal_info else None,
                phone=personal_info.phone if personal_info else None,
                linkedin=personal_info.linkedin if personal_info else None,
                github=personal_info.github if personal_info else None,
                website=personal_info.website if personal_info else None,
                profile_picture_url=self._build_profile_picture_url(profile),
            ),
            career_summary=PublicCareerSummary(
                job_titles=career.job_titles if career else [],
                default_job_title=career.default_job_title if career else "",
                default_summary=career.default_summary if career else "",
                years_of_experience=career.years_of_experience if career else "",
            ),
            life_story=profile.life_story if profile else None,
            work_experience=[
                PublicWorkExperience(
                    job_title=exp.job_title,
                    company=exp.company,
                    location=exp.location,
                    time=exp.time,
                    responsibilities=exp.responsibilities,
                )
                for exp in portfolio.work_experience
            ],
            education=[
                PublicEducation(
                    degree_type=edu.degree_type,
                    degree=edu.degree,
                    university_name=edu.university_name,
                    time=edu.time,
                    location=edu.location,
                    gpa=edu.GPA,
                    transcript=edu.transcript,
                )
                for edu in portfolio.education
            ],
            skills=[
                PublicSkillCategory(category=skill.category, skills=skill.skills)
                for skill in portfolio.skills
            ],
            projects=[
                PublicProject(
                    name=proj.name,
                    bullet_points=proj.bullet_points,
                    date=proj.date,
                    link=str(proj.link) if proj.link else None,
                )
                for proj in portfolio.projects
            ],
            awards=[
                PublicAward(name=award.name, explanation=award.explanation)
                for award in portfolio.awards
            ],
            publications=[
                PublicPublication(
                    name=pub.name,
                    publisher=pub.publisher,
                    link=pub.link,
                    time=pub.time,
                )
                for pub in portfolio.publications
            ],
        )
