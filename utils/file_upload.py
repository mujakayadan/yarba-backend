"""File upload utilities for the Resume Builder application."""

import os
import pathlib
import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

# Set up constants
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
IMAGE_STORAGE_PATH = settings.paths.base_dir / "uploads" / "profile_pictures"


async def validate_image(file: UploadFile) -> Tuple[bool, str]:
    """
    Validate if the file is a valid image and within size limits.

    Args:
        file: The uploaded file

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # Check content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return (
            False,
            f"Unsupported file type: {file.content_type}. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # Check file size
    content = await file.read()
    await file.seek(0)  # Reset file cursor

    if len(content) > MAX_IMAGE_SIZE:
        return False, f"File too large. Maximum size: {MAX_IMAGE_SIZE / 1024 / 1024}MB"

    # Validate image can be opened with PIL
    try:
        from io import BytesIO

        img = Image.open(BytesIO(content))
        img.verify()  # Verify it's a valid image
        return True, ""
    except Exception as e:
        logger.error(f"Invalid image file: {str(e)}")
        return False, "Invalid image file"


async def save_profile_picture(file: UploadFile, user_id: str) -> str:
    """
    Save a profile picture to disk and return the path.

    Args:
        file: The uploaded file
        user_id: User ID to associate with the file

    Returns:
        str: Path to the saved file relative to upload directory
    """
    # Ensure directory exists
    os.makedirs(IMAGE_STORAGE_PATH, exist_ok=True)

    # Validate image
    is_valid, error_message = await validate_image(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    # Create a unique filename with original extension
    original_name = file.filename or "profile"
    file_extension = os.path.splitext(original_name)[1].lower()
    if not file_extension:
        # Default to .jpg if no extension
        file_extension = ".jpg"

    # Format: user_id-uuid.ext
    filename = f"{user_id}-{uuid.uuid4()}{file_extension}"
    file_path = IMAGE_STORAGE_PATH / filename

    # Save the file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Saved profile picture for user {user_id}: {filename}")

    # Return the relative path/filename for storage in the database
    return filename


async def delete_profile_picture(filename: str) -> bool:
    """
    Delete a profile picture from disk.

    Args:
        filename: Filename to delete

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    if not filename:
        return False

    try:
        file_path = IMAGE_STORAGE_PATH / filename
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted profile picture: {filename}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting profile picture {filename}: {str(e)}")
        return False


def get_profile_picture_url(filename: Optional[str]) -> Optional[str]:
    """
    Get the URL for a profile picture.

    Args:
        filename: Filename of the profile picture

    Returns:
        Optional[str]: URL to the profile picture or None
    """
    if not filename:
        return None

    # This could be a static URL or a path depending on your setup
    base_url = settings.api.api_base_url
    return f"{base_url}/static/profile_pictures/{filename}"
