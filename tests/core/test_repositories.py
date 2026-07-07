"""Tests for repositories using Beanie + mongomock."""

import pytest
from beanie import PydanticObjectId

from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from tests.factories import make_portfolio, make_profile, make_resume, make_user


class TestUserRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_by_email(self, beanie_db):
        user = make_user(email="repo@example.com", username="repouser")
        repo = UserRepository()
        created = await repo.create(user)

        found = await repo.get_by_email("repo@example.com")
        assert found is not None
        assert found.id == created.id
        assert found.firebase_uid == user.firebase_uid

    @pytest.mark.asyncio
    async def test_get_by_id(self, beanie_db):
        user = make_user(email="byid@example.com", username="byiduser")
        repo = UserRepository()
        created = await repo.create(user)

        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.email == "byid@example.com"


class TestResumeRepository:
    @pytest.mark.asyncio
    async def test_create_and_get_by_id(self, beanie_db):
        user = make_user(email="resumeowner@example.com", username="resumeowner")
        await user.insert()
        profile = make_profile(user_id=user.id, email=user.email)
        await profile.insert()
        portfolio = make_portfolio(user_id=user.id, profile_id=profile.id)
        await portfolio.insert()

        resume = make_resume(
            user_id=user.id,
            profile_id=profile.id,
            portfolio_id=portfolio.id,
        )
        repo = ResumeRepository()
        created = await repo.create(resume)

        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.title == "Test Resume"
        assert found.user_id == user.id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_missing(self, beanie_db):
        repo = ResumeRepository()
        found = await repo.get_by_id(PydanticObjectId())
        assert found is None
