"""User repository implementation."""

from datetime import UTC, datetime

from beanie import PydanticObjectId
from pydantic import EmailStr

from ..models.portfolio import Portfolio
from ..models.profile import Profile
from ..models.resume import Resume
from ..models.user import User
from ..utils.object_id import ObjectIdLike, coerce_object_id
from .base_repository import BeanieRepository


class UserRepository(BeanieRepository[User]):
    """Repository for User documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(User)

    async def get_by_email(self, email: EmailStr) -> User | None:
        """Get a user by email.

        Args:
            email: User email

        Returns:
            Optional[User]: User if found, None otherwise
        """
        return await User.find_one({"email": email})

    async def get_by_username(self, username: str) -> User | None:
        """Get a user by username.

        Args:
            username: Username

        Returns:
            Optional[User]: User if found, None otherwise
        """
        return await User.find_one({"username": username})

    async def get_by_id(self, user_id: ObjectIdLike) -> User | None:
        """Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            Optional[User]: User if found, None otherwise
        """
        return await User.find_one({"_id": coerce_object_id(user_id)})

    async def get_active_users(self) -> list[User]:
        """Get all active users.

        Returns:
            List[User]: List of active users
        """
        return await User.find({"is_active": True}).to_list()

    async def get_superusers(self) -> list[User]:
        """Get all superusers.

        Returns:
            List[User]: List of superusers
        """
        return await User.find({"is_superuser": True}).to_list()

    async def get_profiles(self, user_id: PydanticObjectId) -> list[Profile]:
        """Get all profiles for a user.

        Args:
            user_id: User ID

        Returns:
            List[Profile]: List of profiles for this user
        """
        return await Profile.find({"user_id": user_id}).to_list()

    async def get_portfolios(self, user_id: PydanticObjectId) -> list[Portfolio]:
        """Get all portfolios for a user.

        Args:
            user_id: User ID

        Returns:
            List[Portfolio]: List of portfolios for this user
        """
        return await Portfolio.find({"user_id": user_id}).to_list()

    async def get_resumes(self, user_id: PydanticObjectId) -> list[Resume]:
        """Get all resumes for a user.

        Args:
            user_id: User ID

        Returns:
            List[Resume]: List of resumes for this user
        """
        return await Resume.find({"user_id": user_id}).to_list()

    async def update_last_login(self, user_id: PydanticObjectId) -> bool:
        """Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful, False otherwise
        """
        result = await User.find_one({"_id": user_id})
        if not result:
            return False

        result.last_login = datetime.now(UTC)
        result.last_active = datetime.now(UTC)
        await result.save()
        return True
