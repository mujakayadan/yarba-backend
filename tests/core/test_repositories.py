"""Tests for repositories."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from ...core.database.repositories.resume import ResumeRepository
from ...core.database.repositories.user import UserRepository
from ...core.exceptions.base import NotFoundException


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


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_create_user(self, mock_database):
        """Test creating a user."""
        # Arrange
        user_data = {
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "full_name": "Test User",
        }

        mock_database.users.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("507f1f77bcf86cd799439011")
        )

        user_repository = UserRepository(database=mock_database)

        # Act
        result = await user_repository.create(user_data)

        # Assert
        assert result["id"] == "507f1f77bcf86cd799439011"
        assert result["email"] == "test@example.com"
        assert result["full_name"] == "Test User"
        assert "hashed_password" in result
        mock_database.users.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_existing_user(self, mock_database):
        """Test finding a user by ID that exists."""
        # Arrange
        user_id = "507f1f77bcf86cd799439011"
        mock_database.users.find_one.return_value = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "full_name": "Test User",
        }

        user_repository = UserRepository(database=mock_database)

        # Act
        result = await user_repository.find_by_id(user_id)

        # Assert
        assert result["id"] == user_id
        assert result["email"] == "test@example.com"
        assert result["full_name"] == "Test User"
        mock_database.users.find_one.assert_called_once_with({"_id": ObjectId(user_id)})

    @pytest.mark.asyncio
    async def test_find_by_id_non_existent_user(self, mock_database):
        """Test finding a user by ID that doesn't exist."""
        # Arrange
        user_id = "507f1f77bcf86cd799439011"
        mock_database.users.find_one.return_value = None

        user_repository = UserRepository(database=mock_database)

        # Act
        result = await user_repository.find_by_id(user_id)

        # Assert
        assert result is None
        mock_database.users.find_one.assert_called_once_with({"_id": ObjectId(user_id)})

    @pytest.mark.asyncio
    async def test_find_by_email_existing_user(self, mock_database):
        """Test finding a user by email that exists."""
        # Arrange
        email = "test@example.com"
        mock_database.users.find_one.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "email": email,
            "hashed_password": "hashed_password",
            "full_name": "Test User",
        }

        user_repository = UserRepository(database=mock_database)

        # Act
        result = await user_repository.find_by_email(email)

        # Assert
        assert result["id"] == "507f1f77bcf86cd799439011"
        assert result["email"] == email
        assert result["full_name"] == "Test User"
        mock_database.users.find_one.assert_called_once_with({"email": email})

    @pytest.mark.asyncio
    async def test_find_by_email_non_existent_user(self, mock_database):
        """Test finding a user by email that doesn't exist."""
        # Arrange
        email = "test@example.com"
        mock_database.users.find_one.return_value = None

        user_repository = UserRepository(database=mock_database)

        # Act
        result = await user_repository.find_by_email(email)

        # Assert
        assert result is None
        mock_database.users.find_one.assert_called_once_with({"email": email})

    @pytest.mark.asyncio
    async def test_update_existing_user(self, mock_database):
        """Test updating an existing user."""
        # Arrange
        user_id = "507f1f77bcf86cd799439011"
        update_data = {
            "full_name": "Updated Name",
        }

        mock_database.users.find_one.return_value = {
            "_id": ObjectId(user_id),
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "full_name": "Test User",
        }

        mock_database.users.update_one.return_value = MagicMock(modified_count=1)

        user_repository = UserRepository(database=mock_database)

        # Act
        result = await user_repository.update(user_id, update_data)

        # Assert
        assert result["id"] == user_id
        assert result["email"] == "test@example.com"
        assert result["full_name"] == "Updated Name"
        mock_database.users.find_one.assert_called_once_with({"_id": ObjectId(user_id)})
        mock_database.users.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_non_existent_user(self, mock_database):
        """Test updating a user that doesn't exist."""
        # Arrange
        user_id = "507f1f77bcf86cd799439011"
        update_data = {
            "full_name": "Updated Name",
        }

        mock_database.users.find_one.return_value = None

        user_repository = UserRepository(database=mock_database)

        # Act & Assert
        with pytest.raises(NotFoundException) as excinfo:
            await user_repository.update(user_id, update_data)

        assert "User not found" in str(excinfo.value)
        mock_database.users.find_one.assert_called_once_with({"_id": ObjectId(user_id)})
        mock_database.users.update_one.assert_not_called()


class TestResumeRepository:
    """Tests for ResumeRepository."""

    @pytest.mark.asyncio
    async def test_create_resume(self, mock_database):
        """Test creating a resume."""
        # Arrange
        resume_data = {
            "title": "Test Resume",
            "user_id": "507f1f77bcf86cd799439011",
            "template_id": "default",
        }

        mock_database.resumes.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("507f1f77bcf86cd799439022")
        )

        resume_repository = ResumeRepository(database=mock_database)

        # Act
        result = await resume_repository.create(resume_data)

        # Assert
        assert result["id"] == "507f1f77bcf86cd799439022"
        assert result["title"] == "Test Resume"
        assert result["user_id"] == "507f1f77bcf86cd799439011"
        assert result["template_id"] == "default"
        mock_database.resumes.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_existing_resume(self, mock_database):
        """Test finding a resume by ID that exists."""
        # Arrange
        resume_id = "507f1f77bcf86cd799439022"
        mock_database.resumes.find_one.return_value = {
            "_id": ObjectId(resume_id),
            "title": "Test Resume",
            "user_id": "507f1f77bcf86cd799439011",
            "template_id": "default",
        }

        resume_repository = ResumeRepository(database=mock_database)

        # Act
        result = await resume_repository.find_by_id(resume_id)

        # Assert
        assert result["id"] == resume_id
        assert result["title"] == "Test Resume"
        assert result["user_id"] == "507f1f77bcf86cd799439011"
        assert result["template_id"] == "default"
        mock_database.resumes.find_one.assert_called_once_with(
            {"_id": ObjectId(resume_id)}
        )

    @pytest.mark.asyncio
    async def test_find_by_id_non_existent_resume(self, mock_database):
        """Test finding a resume by ID that doesn't exist."""
        # Arrange
        resume_id = "507f1f77bcf86cd799439022"
        mock_database.resumes.find_one.return_value = None

        resume_repository = ResumeRepository(database=mock_database)

        # Act
        result = await resume_repository.find_by_id(resume_id)

        # Assert
        assert result is None
        mock_database.resumes.find_one.assert_called_once_with(
            {"_id": ObjectId(resume_id)}
        )

    @pytest.mark.asyncio
    async def test_find_all_by_user_id(self, mock_database):
        """Test finding all resumes for a user."""
        # Arrange
        user_id = "507f1f77bcf86cd799439011"
        mock_cursor = AsyncMock()
        mock_cursor.__aiter__.return_value = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439022"),
                "title": "Resume 1",
                "user_id": user_id,
                "template_id": "default",
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439033"),
                "title": "Resume 2",
                "user_id": user_id,
                "template_id": "modern",
            },
        ]

        mock_database.resumes.find.return_value = mock_cursor

        resume_repository = ResumeRepository(database=mock_database)

        # Act
        result = await resume_repository.find_all(user_id=user_id)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == "507f1f77bcf86cd799439022"
        assert result[0]["title"] == "Resume 1"
        assert result[1]["id"] == "507f1f77bcf86cd799439033"
        assert result[1]["title"] == "Resume 2"
        mock_database.resumes.find.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_resume(self, mock_database):
        """Test updating an existing resume."""
        # Arrange
        resume_id = "507f1f77bcf86cd799439022"
        update_data = {
            "title": "Updated Resume",
            "template_id": "modern",
        }

        mock_database.resumes.find_one.return_value = {
            "_id": ObjectId(resume_id),
            "title": "Test Resume",
            "user_id": "507f1f77bcf86cd799439011",
            "template_id": "default",
        }

        mock_database.resumes.update_one.return_value = MagicMock(modified_count=1)

        resume_repository = ResumeRepository(database=mock_database)

        # Act
        result = await resume_repository.update(resume_id, update_data)

        # Assert
        assert result["id"] == resume_id
        assert result["title"] == "Updated Resume"
        assert result["user_id"] == "507f1f77bcf86cd799439011"
        assert result["template_id"] == "modern"
        mock_database.resumes.find_one.assert_called_once_with(
            {"_id": ObjectId(resume_id)}
        )
        mock_database.resumes.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_non_existent_resume(self, mock_database):
        """Test updating a resume that doesn't exist."""
        # Arrange
        resume_id = "507f1f77bcf86cd799439022"
        update_data = {
            "title": "Updated Resume",
        }

        mock_database.resumes.find_one.return_value = None

        resume_repository = ResumeRepository(database=mock_database)

        # Act & Assert
        with pytest.raises(NotFoundException) as excinfo:
            await resume_repository.update(resume_id, update_data)

        assert "Resume not found" in str(excinfo.value)
        mock_database.resumes.find_one.assert_called_once_with(
            {"_id": ObjectId(resume_id)}
        )
        mock_database.resumes.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_existing_resume(self, mock_database):
        """Test deleting an existing resume."""
        # Arrange
        resume_id = "507f1f77bcf86cd799439022"

        mock_database.resumes.find_one.return_value = {
            "_id": ObjectId(resume_id),
            "title": "Test Resume",
            "user_id": "507f1f77bcf86cd799439011",
            "template_id": "default",
        }

        mock_database.resumes.delete_one.return_value = MagicMock(deleted_count=1)

        resume_repository = ResumeRepository(database=mock_database)

        # Act
        result = await resume_repository.delete(resume_id)

        # Assert
        assert result is True
        mock_database.resumes.find_one.assert_called_once_with(
            {"_id": ObjectId(resume_id)}
        )
        mock_database.resumes.delete_one.assert_called_once_with(
            {"_id": ObjectId(resume_id)}
        )

    @pytest.mark.asyncio
    async def test_delete_non_existent_resume(self, mock_database):
        """Test deleting a resume that doesn't exist."""
        # Arrange
        resume_id = "507f1f77bcf86cd799439022"

        mock_database.resumes.find_one.return_value = None

        resume_repository = ResumeRepository(database=mock_database)

        # Act & Assert
        with pytest.raises(NotFoundException) as excinfo:
            await resume_repository.delete(resume_id)

        assert "Resume not found" in str(excinfo.value)
        mock_database.resumes.find_one.assert_called_once_with(
            {"_id": ObjectId(resume_id)}
        )
        mock_database.resumes.delete_one.assert_not_called()
