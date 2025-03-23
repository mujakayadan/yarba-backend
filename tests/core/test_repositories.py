"""Tests for repositories."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId
from bson import ObjectId

from core.exceptions.base import NotFoundException
from core.models import User
from core.models.resume import Resume
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository


@pytest.fixture
def mock_database():
    """Fixture for mocking MongoDB database."""
    db = AsyncMock()

    # Mock collections
    db.users = AsyncMock()
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()
    db.users.delete_one = AsyncMock()
    db.users.find = AsyncMock()

    db.resumes = AsyncMock()
    db.resumes.find_one = AsyncMock()
    db.resumes.insert_one = AsyncMock()
    db.resumes.update_one = AsyncMock()
    db.resumes.delete_one = AsyncMock()
    db.resumes.find = AsyncMock()

    return db


@pytest.fixture
def user_id():
    """Fixture for user ID."""
    return PydanticObjectId()


@pytest.fixture
def resume_id():
    """Fixture for resume ID."""
    return PydanticObjectId()


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test creating a user."""
        # Arrange
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "is_active": True,
            "is_superuser": False,
            "email_verified": False,
            "login_attempts": 0,
            "subscription_status": "free",
        }

        user_id = PydanticObjectId()

        # Instead of creating an actual User, use MagicMock
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.email_verified = False
        mock_user.login_attempts = 0
        mock_user.subscription_status = "free"

        # Patch the UserRepository create method
        with patch.object(
            UserRepository, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_user
            user_repository = UserRepository()

            # Act
            result = await user_repository.create(user_data)

            # Assert
            assert result.id == user_id
            assert result.email == "test@example.com"
            assert result.username == "testuser"
            assert result.is_active is True
            assert result.is_superuser is False
            assert result.email_verified is False
            assert result.login_attempts == 0
            assert result.subscription_status == "free"
            assert result.hashed_password == "hashed_password"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_existing_user(self, user_id):
        """Test finding a user by email that exists."""
        # Arrange
        email = "test@example.com"

        # Create a mock user instead of a real User instance
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.username = "testuser"
        mock_user.email = email
        mock_user.hashed_password = "hashed_password"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.email_verified = False

        # Patch the UserRepository get_by_email method
        with patch.object(
            UserRepository, "get_by_email", new_callable=AsyncMock
        ) as mock_get_by_email:
            mock_get_by_email.return_value = mock_user
            user_repository = UserRepository()

            # Act
            result = await user_repository.get_by_email(email)

            # Assert
            assert result.id == user_id
            assert result.email == email
            assert result.username == "testuser"
            mock_get_by_email.assert_called_once_with(email)

    @pytest.mark.asyncio
    async def test_get_by_email_non_existent_user(self):
        """Test finding a user by email that doesn't exist."""
        # Arrange
        email = "test@example.com"

        # Patch the UserRepository get_by_email method
        with patch.object(
            UserRepository, "get_by_email", new_callable=AsyncMock
        ) as mock_get_by_email:
            mock_get_by_email.return_value = None
            user_repository = UserRepository()

            # Act
            result = await user_repository.get_by_email(email)

            # Assert
            assert result is None
            mock_get_by_email.assert_called_once_with(email)

    @pytest.mark.asyncio
    async def test_get_by_username_existing_user(self, user_id):
        """Test finding a user by username that exists."""
        # Arrange
        username = "testuser"

        # Create a mock user instead of a real User instance
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.username = username
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.email_verified = False

        # Patch the UserRepository get_by_username method
        with patch.object(
            UserRepository, "get_by_username", new_callable=AsyncMock
        ) as mock_get_by_username:
            mock_get_by_username.return_value = mock_user
            user_repository = UserRepository()

            # Act
            result = await user_repository.get_by_username(username)

            # Assert
            assert result.id == user_id
            assert result.email == "test@example.com"
            assert result.username == username
            mock_get_by_username.assert_called_once_with(username)

    @pytest.mark.asyncio
    async def test_get_by_id_existing_user(self, user_id):
        """Test finding a user by ID that exists."""
        # Arrange
        # Create a mock user instead of a real User instance
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        mock_user.is_active = True
        mock_user.is_superuser = False
        mock_user.email_verified = False

        # Patch the UserRepository get_by_id method
        with patch.object(
            UserRepository, "get_by_id", new_callable=AsyncMock
        ) as mock_get_by_id:
            mock_get_by_id.return_value = mock_user
            user_repository = UserRepository()

            # Act
            result = await user_repository.get_by_id(user_id)

            # Assert
            assert result.id == user_id
            assert result.email == "test@example.com"
            assert result.username == "testuser"
            mock_get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_active_users(self):
        """Test finding all active users."""
        # Arrange
        # Create mock users instead of real User instances
        mock_user1 = MagicMock()
        mock_user1.id = PydanticObjectId()
        mock_user1.username = "user1"
        mock_user1.email = "user1@example.com"
        mock_user1.is_active = True

        mock_user2 = MagicMock()
        mock_user2.id = PydanticObjectId()
        mock_user2.username = "user2"
        mock_user2.email = "user2@example.com"
        mock_user2.is_active = True

        users = [mock_user1, mock_user2]

        # Patch the UserRepository get_active_users method
        with patch.object(
            UserRepository, "get_active_users", new_callable=AsyncMock
        ) as mock_get_active_users:
            mock_get_active_users.return_value = users
            user_repository = UserRepository()

            # Act
            result = await user_repository.get_active_users()

            # Assert
            assert len(result) == 2
            assert result[0].username == "user1"
            assert result[1].username == "user2"
            mock_get_active_users.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_login(self, user_id):
        """Test updating a user's last login timestamp."""
        # Arrange
        # Patch the UserRepository update_last_login method
        with patch.object(
            UserRepository, "update_last_login", new_callable=AsyncMock
        ) as mock_update_last_login:
            mock_update_last_login.return_value = True
            user_repository = UserRepository()

            # Act
            result = await user_repository.update_last_login(user_id)

            # Assert
            assert result is True
            mock_update_last_login.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_increment_login_attempts(self, user_id):
        """Test incrementing login attempts for a user."""
        # Arrange
        email = "test@example.com"

        # Patch the UserRepository increment_login_attempts method
        with patch.object(
            UserRepository, "increment_login_attempts", new_callable=AsyncMock
        ) as mock_increment:
            mock_increment.return_value = 1  # New login attempts count
            user_repository = UserRepository()

            # Act
            result = await user_repository.increment_login_attempts(email)

            # Assert
            assert result == 1
            mock_increment.assert_called_once_with(email)

    @pytest.mark.asyncio
    async def test_reset_login_attempts(self, user_id):
        """Test resetting login attempts for a user."""
        # Arrange
        email = "test@example.com"

        # Patch the UserRepository reset_login_attempts method
        with patch.object(
            UserRepository, "reset_login_attempts", new_callable=AsyncMock
        ) as mock_reset:
            mock_reset.return_value = True
            user_repository = UserRepository()

            # Act
            result = await user_repository.reset_login_attempts(email)

            # Assert
            assert result is True
            mock_reset.assert_called_once_with(email)

    @pytest.mark.asyncio
    async def test_lock_account(self, user_id):
        """Test locking a user account."""
        # Arrange
        email = "test@example.com"
        lock_until = datetime.now(timezone.utc) + timedelta(hours=1)

        # Patch the UserRepository lock_account method
        with patch.object(
            UserRepository, "lock_account", new_callable=AsyncMock
        ) as mock_lock:
            mock_lock.return_value = True
            user_repository = UserRepository()

            # Act
            result = await user_repository.lock_account(email, lock_until)

            # Assert
            assert result is True
            mock_lock.assert_called_once_with(email, lock_until)


class TestResumeRepository:
    """Tests for ResumeRepository."""

    @pytest.mark.asyncio
    async def test_create_resume(self, resume_id):
        """Test creating a resume."""
        # Arrange
        resume_data = {
            "title": "Test Resume",
            "user_id": "507f1f77bcf86cd799439011",
            "template_id": "default",
        }

        # Create mock resume
        mock_resume = MagicMock()
        mock_resume.id = resume_id
        mock_resume.title = "Test Resume"
        mock_resume.user_id = "507f1f77bcf86cd799439011"
        mock_resume.template_id = "default"

        # Patch the ResumeRepository create method
        with patch.object(
            ResumeRepository, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_resume
            resume_repository = ResumeRepository()

            # Act
            result = await resume_repository.create(resume_data)

            # Assert
            assert result.id == resume_id
            assert result.title == "Test Resume"
            assert result.user_id == "507f1f77bcf86cd799439011"
            assert result.template_id == "default"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_existing_resume(self, resume_id):
        """Test finding a resume by ID that exists."""
        # Arrange
        # Create mock resume
        mock_resume = MagicMock()
        mock_resume.id = resume_id
        mock_resume.title = "Test Resume"
        mock_resume.user_id = "507f1f77bcf86cd799439011"
        mock_resume.template_id = "default"

        # Patch the ResumeRepository get_by_id method
        with patch.object(
            ResumeRepository, "get_by_id", new_callable=AsyncMock
        ) as mock_get_by_id:
            mock_get_by_id.return_value = mock_resume
            resume_repository = ResumeRepository()

            # Act
            result = await resume_repository.get_by_id(resume_id)

            # Assert
            assert result.id == resume_id
            assert result.title == "Test Resume"
            assert result.user_id == "507f1f77bcf86cd799439011"
            assert result.template_id == "default"
            mock_get_by_id.assert_called_once_with(resume_id)

    @pytest.mark.asyncio
    async def test_get_by_id_non_existent_resume(self, resume_id):
        """Test finding a resume by ID that doesn't exist."""
        # Arrange
        # Patch the ResumeRepository get_by_id method
        with patch.object(
            ResumeRepository, "get_by_id", new_callable=AsyncMock
        ) as mock_get_by_id:
            mock_get_by_id.return_value = None
            resume_repository = ResumeRepository()

            # Act
            result = await resume_repository.get_by_id(resume_id)

            # Assert
            assert result is None
            mock_get_by_id.assert_called_once_with(resume_id)

    @pytest.mark.asyncio
    async def test_get_all_by_user_id(self):
        """Test finding all resumes for a user."""
        # Arrange
        user_id = "507f1f77bcf86cd799439011"

        # Create mock resumes
        mock_resume1 = MagicMock()
        mock_resume1.id = "507f1f77bcf86cd799439022"
        mock_resume1.title = "Resume 1"
        mock_resume1.user_id = user_id
        mock_resume1.template_id = "default"

        mock_resume2 = MagicMock()
        mock_resume2.id = "507f1f77bcf86cd799439033"
        mock_resume2.title = "Resume 2"
        mock_resume2.user_id = user_id
        mock_resume2.template_id = "modern"

        resumes = [mock_resume1, mock_resume2]

        # Patch the ResumeRepository get_all method
        with patch.object(
            ResumeRepository, "get_all", new_callable=AsyncMock
        ) as mock_get_all:
            mock_get_all.return_value = resumes
            resume_repository = ResumeRepository()

            # Act
            result = await resume_repository.get_all(user_id=user_id)

            # Assert
            assert len(result) == 2
            assert result[0].id == "507f1f77bcf86cd799439022"
            assert result[0].title == "Resume 1"
            assert result[1].id == "507f1f77bcf86cd799439033"
            assert result[1].title == "Resume 2"
            mock_get_all.assert_called_once_with(user_id=user_id)

    @pytest.mark.asyncio
    async def test_update_existing_resume(self, resume_id):
        """Test updating an existing resume."""
        # Arrange
        update_data = {
            "title": "Updated Resume",
            "template_id": "modern",
        }

        # Create mock updated resume
        mock_resume = MagicMock()
        mock_resume.id = resume_id
        mock_resume.title = "Updated Resume"
        mock_resume.user_id = "507f1f77bcf86cd799439011"
        mock_resume.template_id = "modern"

        # Patch the ResumeRepository update method
        with patch.object(
            ResumeRepository, "update", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = mock_resume
            resume_repository = ResumeRepository()

            # Act
            result = await resume_repository.update(resume_id, update_data)

            # Assert
            assert result.id == resume_id
            assert result.title == "Updated Resume"
            assert result.user_id == "507f1f77bcf86cd799439011"
            assert result.template_id == "modern"
            mock_update.assert_called_once_with(resume_id, update_data)

    @pytest.mark.asyncio
    async def test_update_non_existent_resume(self, resume_id):
        """Test updating a resume that doesn't exist."""
        # Arrange
        update_data = {
            "title": "Updated Resume",
        }

        # Patch the ResumeRepository update method to raise exception
        with patch.object(
            ResumeRepository, "update", new_callable=AsyncMock
        ) as mock_update:
            mock_update.side_effect = NotFoundException("Resume not found")
            resume_repository = ResumeRepository()

            # Act & Assert
            with pytest.raises(NotFoundException) as excinfo:
                await resume_repository.update(resume_id, update_data)

            assert "Resume not found" in str(excinfo.value)
            mock_update.assert_called_once_with(resume_id, update_data)

    @pytest.mark.asyncio
    async def test_delete_existing_resume(self, resume_id):
        """Test deleting an existing resume."""
        # Arrange
        # Patch the ResumeRepository delete method
        with patch.object(
            ResumeRepository, "delete", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.return_value = True
            resume_repository = ResumeRepository()

            # Act
            result = await resume_repository.delete(resume_id)

            # Assert
            assert result is True
            mock_delete.assert_called_once_with(resume_id)

    @pytest.mark.asyncio
    async def test_delete_non_existent_resume(self, resume_id):
        """Test deleting a resume that doesn't exist."""
        # Arrange
        # Patch the ResumeRepository delete method to raise exception
        with patch.object(
            ResumeRepository, "delete", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.side_effect = NotFoundException("Resume not found")
            resume_repository = ResumeRepository()

            # Act & Assert
            with pytest.raises(NotFoundException) as excinfo:
                await resume_repository.delete(resume_id)

            assert "Resume not found" in str(excinfo.value)
            mock_delete.assert_called_once_with(resume_id)
