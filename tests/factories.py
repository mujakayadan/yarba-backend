"""Test data factories aligned with current Beanie models."""

from beanie import PydanticObjectId

from core.models.cover_letter import CoverLetter
from core.models.portfolio import Portfolio
from core.models.profile import PersonalInformation, Profile
from core.models.resume import Resume
from core.models.user import User

TEST_USER_ID = PydanticObjectId("507f1f77bcf86cd799439011")
TEST_PROFILE_ID = PydanticObjectId("507f1f77bcf86cd799439022")
TEST_PORTFOLIO_ID = PydanticObjectId("507f1f77bcf86cd799439033")
TEST_RESUME_ID = PydanticObjectId("507f1f77bcf86cd799439044")
TEST_COVER_LETTER_ID = PydanticObjectId("507f1f77bcf86cd799439055")


def make_user(
    *,
    email: str = "test@example.com",
    username: str = "testuser",
    firebase_uid: str = "firebase-test-uid",
    **kwargs,
) -> User:
    return User(
        email=email,
        username=username,
        firebase_uid=firebase_uid,
        auth_provider="firebase.password",
        is_active=True,
        email_verified=True,
        **kwargs,
    )


def make_profile(
    *,
    user_id: PydanticObjectId,
    email: str = "test@example.com",
    **kwargs,
) -> Profile:
    personal = kwargs.pop(
        "personal_information",
        PersonalInformation(email=email, full_name="Test User"),
    )
    return Profile(
        user_id=user_id,
        personal_information=personal,
        **kwargs,
    )


def make_portfolio(
    *,
    user_id: PydanticObjectId,
    profile_id: PydanticObjectId,
    **kwargs,
) -> Portfolio:
    return Portfolio(
        user_id=user_id,
        profile_id=profile_id,
        **kwargs,
    )


def make_resume(
    *,
    user_id: PydanticObjectId,
    profile_id: PydanticObjectId,
    portfolio_id: PydanticObjectId,
    **kwargs,
) -> Resume:
    defaults = {
        "title": "Test Resume",
        "template_id": "default",
        "job_description": "Software engineer role requiring Python.",
        "content": {"summary": "Experienced developer."},
    }
    defaults.update(kwargs)
    return Resume(
        user_id=user_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
        **defaults,
    )


def make_cover_letter(
    *,
    user_id: PydanticObjectId,
    resume_id: PydanticObjectId,
    profile_id: PydanticObjectId | None = None,
    portfolio_id: PydanticObjectId | None = None,
    **kwargs,
) -> CoverLetter:
    defaults = {
        "template_id": "default",
        "content": "Dear hiring manager, this is a test cover letter.",
    }
    defaults.update(kwargs)
    return CoverLetter(
        user_id=user_id,
        resume_id=resume_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
        **defaults,
    )
