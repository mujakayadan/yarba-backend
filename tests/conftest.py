"""Shared pytest fixtures for the Yarba backend test suite."""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from beanie import init_beanie
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from tests.support.async_mongo_mock import AsyncMongoMockClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI

from api.dependencies.auth import get_current_active_user
from api.dependencies.database import (
    get_portfolio_repository,
    get_profile_repository,
    get_resume_repository,
    get_user_repository,
)
from api.dependencies.services import (
    get_cover_letter_generation_service,
    get_resume_generation_service,
)
from api.main import app as fastapi_app
from api.middleware.auth import get_current_user
from core.database.factory import get_auth_service
from core.models.cover_letter import CoverLetter
from core.models.inbound_email import InboundEmail
from core.models.portfolio import Portfolio
from core.models.portfolio_website import PortfolioWebsite
from core.models.profile import Profile
from core.models.resume import Resume
from core.models.user import User
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from core.services.auth_service import AuthService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService
from tests.factories import (
    make_cover_letter,
    make_portfolio,
    make_profile,
    make_resume,
    make_user,
)


async def _resume_data_bundle(resume_id):
    resume = await Resume.get(resume_id)
    profile = await Profile.find_one(Profile.user_id == resume.user_id)
    portfolio = await Portfolio.find_one(Portfolio.user_id == resume.user_id)
    return resume, profile, portfolio


BEANIE_DOCUMENT_MODELS = [
    User,
    Resume,
    CoverLetter,
    Profile,
    Portfolio,
    PortfolioWebsite,
    InboundEmail,
]

_test_mongo_client: AsyncMongoMockClient | None = None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide stable test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DB", "test_db")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret_key_for_jwt_signing_32chars")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("AWS_BUCKET", "yarba-local")


@pytest.fixture
async def beanie_db() -> AsyncIterator[AsyncMongoMockClient]:
    """Initialize Beanie against an in-memory MongoDB mock."""
    global _test_mongo_client
    _test_mongo_client = AsyncMongoMockClient()
    await init_beanie(
        database=_test_mongo_client["test_db"],
        document_models=BEANIE_DOCUMENT_MODELS,
    )
    yield _test_mongo_client
    # Always clear via the mock client handle — never model.get_pymongo_collection(),
    # which follows Beanie's global connection and could point at a real database
    # if app lifespan re-initialized Beanie during the test.
    test_db = _test_mongo_client["test_db"]
    for model in BEANIE_DOCUMENT_MODELS:
        await test_db[model.Settings.name].delete_many({})
    _test_mongo_client = None


@pytest.fixture
async def test_user(beanie_db: AsyncMongoMockClient) -> User:
    user = make_user()
    await user.insert()
    return user


@pytest.fixture
def mock_current_user(test_user: User) -> User:
    return test_user


@pytest.fixture
async def test_profile(test_user: User, beanie_db: AsyncMongoMockClient) -> Profile:
    profile = make_profile(user_id=test_user.id)
    await profile.insert()
    return profile


@pytest.fixture
async def test_portfolio(
    test_user: User, test_profile: Profile, beanie_db: AsyncMongoMockClient
) -> Portfolio:
    portfolio = make_portfolio(user_id=test_user.id, profile_id=test_profile.id)
    await portfolio.insert()
    return portfolio


@pytest.fixture
async def test_resume(
    test_user: User,
    test_profile: Profile,
    test_portfolio: Portfolio,
    beanie_db: AsyncMongoMockClient,
) -> Resume:
    resume = make_resume(
        user_id=test_user.id,
        profile_id=test_profile.id,
        portfolio_id=test_portfolio.id,
    )
    await resume.insert()
    return resume


@pytest.fixture
async def test_cover_letter(
    test_user: User,
    test_profile: Profile,
    test_portfolio: Portfolio,
    test_resume: Resume,
    beanie_db: AsyncMongoMockClient,
) -> CoverLetter:
    cover_letter = make_cover_letter(
        user_id=test_user.id,
        profile_id=test_profile.id,
        portfolio_id=test_portfolio.id,
        resume_id=test_resume.id,
    )
    await cover_letter.insert()
    return cover_letter


@pytest.fixture
def app() -> FastAPI:
    return fastapi_app


@pytest.fixture
def mock_user_repository() -> AsyncMock:
    repository = AsyncMock(spec=UserRepository)
    repository.get_by_email = AsyncMock()
    repository.create = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_profile_repository() -> AsyncMock:
    repository = AsyncMock(spec=ProfileRepository)
    repository.get_by_id = AsyncMock()
    repository.get_by_user_id = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_portfolio_repository() -> AsyncMock:
    repository = AsyncMock(spec=PortfolioRepository)
    repository.get_by_id = AsyncMock()
    repository.get_by_user_id = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_resume_repository() -> AsyncMock:
    repository = AsyncMock(spec=ResumeRepository)
    repository.get_by_id = AsyncMock()
    repository.get_all_by_user_id = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_auth_service(mock_user_repository: AsyncMock) -> AsyncMock:
    service = AsyncMock(spec=AuthService)
    service.register_with_firebase = AsyncMock()
    service.login_with_firebase = AsyncMock()
    service.create_access_token = AsyncMock()
    service.verify_token = AsyncMock()
    service.user_repository = mock_user_repository
    return service


@pytest.fixture
def mock_resume_service(mock_resume_repository: AsyncMock) -> AsyncMock:
    service = AsyncMock(spec=ResumeService)
    service.create_resume = AsyncMock()
    service.get_resume = AsyncMock()
    service.get_all_resumes = AsyncMock()
    service.update_resume = AsyncMock()
    service.delete_resume = AsyncMock()
    service.resume_repository = mock_resume_repository
    return service


@pytest.fixture
def mock_latex_service() -> AsyncMock:
    service = AsyncMock(spec=LatexService)
    service.generate_resume_latex = AsyncMock()
    service.generate_cover_letter_latex = AsyncMock()
    service.compile_latex_to_pdf = AsyncMock()
    return service


@pytest.fixture
def mock_tex_service() -> AsyncMock:
    return AsyncMock(spec=LatexService)


@pytest.fixture
def mock_llm_service(mock_profile_repository: AsyncMock) -> AsyncMock:
    service = AsyncMock(spec=LLMService)
    service.generate_cover_letter = AsyncMock()
    service.get_completion = AsyncMock()
    service.configure_for_user = AsyncMock()
    service.profile_repository = mock_profile_repository
    return service


@pytest.fixture
def mock_prompt_service() -> AsyncMock:
    service = AsyncMock(spec=PromptService)
    service.get_prompt = AsyncMock()
    service.get_system_prompt = AsyncMock()
    service.get_cover_letter_prompt = AsyncMock()
    service.get_portfolio_section_prompt = AsyncMock()
    return service


@pytest.fixture
def mock_resume_generation_service(
    mock_resume_repository: AsyncMock,
    mock_profile_repository: AsyncMock,
    mock_portfolio_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    mock_tex_service: AsyncMock,
) -> AsyncMock:
    service = AsyncMock(spec=ResumeGenerationService)
    service.generate_resume_content = AsyncMock()
    service.generate_cover_letter = AsyncMock()
    service.generate_resume_textual_content = AsyncMock()
    service.compile_pdf = AsyncMock(return_value=b"%PDF-1.4 test")
    service.llm = mock_llm_service
    service.tex = mock_tex_service
    service.resume_repository = mock_resume_repository
    service.profile_repository = mock_profile_repository
    service.portfolio_repository = mock_portfolio_repository
    return service


async def _mock_init_db() -> AsyncMongoMockClient:
    """Reuse the same mongomock client as test fixtures (app lifespan calls init_db)."""
    global _test_mongo_client
    if _test_mongo_client is None:
        _test_mongo_client = AsyncMongoMockClient()
        await init_beanie(
            database=_test_mongo_client["test_db"],
            document_models=BEANIE_DOCUMENT_MODELS,
        )
    return _test_mongo_client


@pytest.fixture
async def async_client(
    test_user: User,
    test_profile: Profile,
    test_portfolio: Portfolio,
    mock_resume_generation_service: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    """HTTP client with mocked DB startup and authenticated user."""

    async def _populate_resume_text(resume_id) -> None:
        resume = await Resume.get(resume_id)
        if resume:
            resume.content = {"summary": "Generated test content"}
            await resume.save()

    mock_resume_generation_service.generate_resume_textual_content = AsyncMock(
        side_effect=_populate_resume_text
    )
    mock_resume_generation_service.compile_pdf = AsyncMock(return_value=b"%PDF-1.4")
    mock_resume_generation_service.get_resume_data = AsyncMock(
        side_effect=_resume_data_bundle
    )

    async def _populate_cover_letter(cover_letter_id) -> None:
        cover_letter = await CoverLetter.get(cover_letter_id)
        if cover_letter:
            cover_letter.content = "Generated cover letter content"
            await cover_letter.save()

    mock_cover_letter_generation = AsyncMock()
    mock_cover_letter_generation.generate_cover_letter_content = AsyncMock(
        side_effect=_populate_cover_letter
    )
    mock_cover_letter_generation.generate_pdf = AsyncMock(return_value=b"%PDF-1.4")

    monkeypatch.setattr("api.main.init_db", _mock_init_db)
    monkeypatch.setattr("core.database.init.init_db", _mock_init_db)
    monkeypatch.setattr("core.auth.firebase.FirebaseAuth.initialize", lambda: True)

    async def override_active_user() -> User:
        return test_user

    fastapi_app.dependency_overrides[get_current_user] = override_active_user
    fastapi_app.dependency_overrides[get_current_active_user] = override_active_user
    fastapi_app.dependency_overrides[get_resume_generation_service] = lambda: (
        mock_resume_generation_service
    )
    fastapi_app.dependency_overrides[get_cover_letter_generation_service] = lambda: (
        mock_cover_letter_generation
    )

    transport = ASGITransport(app=fastapi_app)
    async with fastapi_app.router.lifespan_context(fastapi_app):
        # Re-seed after lifespan init_db so API services see the same database state
        if await User.get(test_user.id) is None:
            await test_user.insert()
        if await Profile.find_one(Profile.user_id == test_user.id) is None:
            profile = make_profile(user_id=test_user.id)
            await profile.insert()
        if await Portfolio.find_one(Portfolio.user_id == test_user.id) is None:
            profile_doc = await Profile.find_one(Profile.user_id == test_user.id)
            portfolio = make_portfolio(user_id=test_user.id, profile_id=profile_doc.id)
            await portfolio.insert()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def mock_get_current_user(test_user: User):
    async def _get_current_user() -> User:
        return test_user

    return _get_current_user


@pytest.fixture
def app_with_mocked_dependencies(
    app,
    mock_user_repository,
    mock_profile_repository,
    mock_portfolio_repository,
    mock_resume_repository,
    mock_get_current_user,
):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repository
    app.dependency_overrides[get_profile_repository] = lambda: mock_profile_repository
    app.dependency_overrides[get_portfolio_repository] = lambda: (
        mock_portfolio_repository
    )
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repository
    return app


@pytest.fixture
def client(app_with_mocked_dependencies) -> TestClient:
    return TestClient(app_with_mocked_dependencies)


@pytest.fixture
def client_with_mocked_dependencies(app_with_mocked_dependencies) -> TestClient:
    return TestClient(app_with_mocked_dependencies)


@pytest.fixture
def registered_user() -> dict[str, str]:
    return {
        "email": "registered@example.com",
        "password": "Password123!",
    }


@pytest.fixture
async def async_client_auth(
    async_client: AsyncClient, mock_auth_service: AsyncMock
) -> AsyncIterator[AsyncClient]:
    """Async client with mocked Firebase auth service."""
    mock_auth_service.register_with_firebase = AsyncMock(
        return_value={
            "user": {
                "id": "507f1f77bcf86cd799439011",
                "email": "newuser@example.com",
                "username": "newuser",
            },
            "access_token": "test-access-token",
            "token_type": "bearer",
            "is_new_user": True,
            "current_setup_step": 1,
        }
    )

    async def duplicate_register(*_args, **_kwargs):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Email already registered")

    mock_auth_service.login_with_firebase = AsyncMock(
        return_value={
            "user": {
                "id": "507f1f77bcf86cd799439011",
                "email": "registered@example.com",
            },
            "access_token": "test-access-token",
            "token_type": "bearer",
        }
    )

    fastapi_app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    yield async_client
    fastapi_app.dependency_overrides.pop(get_auth_service, None)
