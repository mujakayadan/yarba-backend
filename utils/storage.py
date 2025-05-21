"""Storage utilities for the Resume Builder application."""

import os
import time
import uuid
from io import BytesIO
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError
from botocore.signers import CloudFrontSigner
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class StorageProvider:
    """Base class for storage providers."""

    async def validate_image(self, file: UploadFile) -> Tuple[bool, str]:
        """
        Validate if the file is a valid image and within size limits.

        Args:
            file: The uploaded file

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Check content type
        if file.content_type not in settings.storage.allowed_image_types:
            return (
                False,
                f"Unsupported file type: {file.content_type}. Allowed types: {', '.join(settings.storage.allowed_image_types)}",
            )

        # Check file size
        content = await file.read()
        await file.seek(0)  # Reset file cursor

        if len(content) > settings.storage.max_image_size:
            return (
                False,
                f"File too large. Maximum size: {settings.storage.max_image_size / 1024 / 1024}MB",
            )

        # Validate image can be opened with PIL
        try:
            img = Image.open(BytesIO(content))
            img.verify()  # Verify it's a valid image
            return True, ""
        except Exception as e:
            logger.error(f"Invalid image file: {str(e)}")
            return False, "Invalid image file"

    async def validate_pdf(self, content: bytes) -> Tuple[bool, str]:
        """
        Validate if the content is a valid PDF and within size limits.

        Args:
            content: PDF content

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        # Check file size
        if len(content) > settings.storage.max_pdf_size:
            return (
                False,
                f"PDF too large. Maximum size: {settings.storage.max_pdf_size / 1024 / 1024}MB",
            )

        # Check for PDF magic number (%PDF-) at the beginning of the file
        if not content.startswith(b"%PDF-"):
            return False, "Not a valid PDF file (missing PDF header)"

        return True, ""

    async def save_profile_picture(self, file: UploadFile, user_id: str) -> str:
        """
        Save a profile picture and return the path/URL.

        Args:
            file: The uploaded file
            user_id: User ID to associate with the file

        Returns:
            str: Path or URL to the saved file
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    async def save_signature(self, signature_data: bytes, user_id: str) -> str:
        """
        Save a signature and return the path/URL.

        Args:
            signature_data: Signature binary data
            user_id: User ID to associate with the file

        Returns:
            str: Path or URL to the saved file
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    async def save_resume_pdf(self, pdf_data: bytes, resume_id: str) -> str:
        """
        Save a resume PDF and return the path/URL.

        Args:
            pdf_data: PDF binary data
            resume_id: Resume ID to associate with the file

        Returns:
            str: Path or URL to the saved file
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    async def save_cover_letter_pdf(self, pdf_data: bytes, cover_letter_id: str) -> str:
        """
        Save a cover letter PDF and return the path/URL.

        Args:
            pdf_data: PDF binary data
            cover_letter_id: Cover letter ID to associate with the file

        Returns:
            str: Path or URL to the saved file
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    async def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            object_key: Key/path of the file to delete

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        raise NotImplementedError("This method should be implemented by subclasses")

    def get_url(self, object_key: Optional[str]) -> Optional[str]:
        """
        Get the URL for an object.

        Args:
            object_key: Key/path of the object

        Returns:
            Optional[str]: URL to the object or None
        """
        raise NotImplementedError("This method should be implemented by subclasses")


class LocalStorageProvider(StorageProvider):
    """Provider for local filesystem storage."""

    async def save_profile_picture(self, file: UploadFile, user_id: str) -> str:
        """Save a profile picture to local disk."""
        # Ensure directory exists
        storage_path = (
            settings.paths.base_dir
            / settings.storage.local_storage_path
            / settings.storage.profile_pictures_path
        )
        os.makedirs(storage_path, exist_ok=True)

        # Validate image
        is_valid, error_message = await self.validate_image(file)
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
        file_path = storage_path / filename

        # Save the file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved profile picture for user {user_id}: {filename}")

        # Return the relative path for the object key
        return f"{settings.storage.profile_pictures_path}/{filename}"

    async def save_signature(self, signature_data: bytes, user_id: str) -> str:
        """Save a signature to local disk."""
        # Ensure directory exists
        storage_path = (
            settings.paths.base_dir
            / settings.storage.local_storage_path
            / settings.storage.signatures_path
        )
        os.makedirs(storage_path, exist_ok=True)

        # Format: user_id-uuid.png
        filename = f"{user_id}-{uuid.uuid4()}.png"
        file_path = storage_path / filename

        # Save the file
        with open(file_path, "wb") as f:
            f.write(signature_data)

        logger.info(f"Saved signature for user {user_id}: {filename}")

        # Return the relative path for the object key
        return f"{settings.storage.signatures_path}/{filename}"

    async def save_resume_pdf(self, pdf_data: bytes, resume_id: str) -> str:
        """Save a resume PDF to local disk."""
        # Ensure directory exists
        storage_path = (
            settings.paths.base_dir
            / settings.storage.local_storage_path
            / settings.storage.resumes_path
        )
        os.makedirs(storage_path, exist_ok=True)

        # Validate PDF
        is_valid, error_message = await self.validate_pdf(pdf_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
            )

        # Format: resume_id-uuid.pdf
        filename = f"{resume_id}-{uuid.uuid4()}.pdf"
        file_path = storage_path / filename

        # Save the file
        with open(file_path, "wb") as f:
            f.write(pdf_data)

        logger.info(f"Saved resume PDF for resume {resume_id}: {filename}")

        # Return the relative path for the object key
        return f"{settings.storage.resumes_path}/{filename}"

    async def save_cover_letter_pdf(self, pdf_data: bytes, cover_letter_id: str) -> str:
        """Save a cover letter PDF to local disk."""
        # Ensure directory exists
        storage_path = (
            settings.paths.base_dir
            / settings.storage.local_storage_path
            / settings.storage.cover_letters_path
        )
        os.makedirs(storage_path, exist_ok=True)

        # Validate PDF
        is_valid, error_message = await self.validate_pdf(pdf_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
            )

        # Format: cover_letter_id-uuid.pdf
        filename = f"{cover_letter_id}-{uuid.uuid4()}.pdf"
        file_path = storage_path / filename

        # Save the file
        with open(file_path, "wb") as f:
            f.write(pdf_data)

        logger.info(
            f"Saved cover letter PDF for cover letter {cover_letter_id}: {filename}"
        )

        # Return the relative path for the object key
        return f"{settings.storage.cover_letters_path}/{filename}"

    async def delete_file(self, object_key: str) -> bool:
        """Delete a file from local disk."""
        if not object_key:
            return False

        try:
            # Parse the object key to get the path relative to local storage
            path_parts = object_key.split("/")
            if not path_parts:
                return False

            # Reconstruct the full path
            storage_path = settings.paths.base_dir / settings.storage.local_storage_path
            file_path = storage_path / object_key

            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {object_key}")
                return True

            logger.warning(f"File not found for deletion: {object_key}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file {object_key}: {str(e)}")
            return False

    def get_url(self, object_key: Optional[str]) -> Optional[str]:
        """Get the URL for a local file."""
        if not object_key:
            return None

        # Get the path components
        path_parts = object_key.split("/")
        if len(path_parts) < 2:
            return None

        path_parts[0]  # First part should be the asset type (e.g., profile-pictures)

        # Return a URL path that will be served by the static file handler
        return f"{settings.api.api_base_url}/static/{object_key}"


class AWSS3StorageProvider(StorageProvider):
    """Provider for AWS S3 storage."""

    def __init__(self):
        """Initialize connection to AWS S3 and CloudFront."""
        self.session = boto3.session.Session(
            aws_access_key_id=settings.storage.aws_access_key,
            aws_secret_access_key=settings.storage.aws_secret_key,
            region_name=settings.storage.aws_region,
        )
        self.s3_client = self.session.client("s3")
        self.bucket = settings.storage.aws_bucket

        # Initialize CloudFront signer if enabled
        self.cloudfront_enabled = settings.storage.cloudfront_enabled
        self.cloudfront_domain = settings.storage.cloudfront_domain

        if self.cloudfront_enabled and self.cloudfront_domain:
            logger.info(f"CloudFront distribution enabled: {self.cloudfront_domain}")

            # Initialize CloudFront signer for private content if key pair is configured
            self.cloudfront_signer = None
            if (
                settings.storage.cloudfront_key_pair_id
                and settings.storage.cloudfront_private_key_path
                and os.path.exists(settings.storage.cloudfront_private_key_path)
            ):

                try:
                    with open(
                        settings.storage.cloudfront_private_key_path, "rb"
                    ) as key_file:
                        private_key = serialization.load_pem_private_key(
                            key_file.read(), password=None, backend=default_backend()
                        )

                    self.cloudfront_signer = CloudFrontSigner(
                        settings.storage.cloudfront_key_pair_id,
                        self._rsa_signer(private_key),
                    )
                    logger.info("CloudFront signer initialized for signed URLs")
                except Exception as e:
                    logger.error(f"Failed to initialize CloudFront signer: {str(e)}")

        # Check S3 connection
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            logger.info(f"Successfully connected to AWS S3 bucket: {self.bucket}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                logger.error(f"AWS S3 bucket does not exist: {self.bucket}")
            elif error_code == "403":
                logger.error(f"Access forbidden to AWS S3 bucket: {self.bucket}")
            else:
                logger.error(f"Error connecting to AWS S3: {str(e)}")

    def _rsa_signer(self, private_key):
        """Create a RSA signer for CloudFront signed URLs."""

        def sign_string(message):
            return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

        return sign_string

    async def save_profile_picture(self, file: UploadFile, user_id: str) -> str:
        """Upload a profile picture to AWS S3."""
        # Validate image
        is_valid, error_message = await self.validate_image(file)
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

        # Format: profile-pictures/user_id-uuid.ext
        object_key = f"{settings.storage.profile_pictures_path}/{user_id}-{uuid.uuid4()}{file_extension}"

        # Upload to S3
        try:
            content = await file.read()

            # Upload with appropriate content type
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=content,
                ContentType=file.content_type,
            )

            logger.info(f"Uploaded profile picture to AWS S3: {object_key}")

            # Return the object key for storage in the database
            return object_key
        except Exception as e:
            logger.error(f"Error uploading profile picture to S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file: {str(e)}",
            )

    async def save_signature(self, signature_data: bytes, user_id: str) -> str:
        """Upload a signature to AWS S3."""
        # Format: signatures/user_id-uuid.png
        object_key = f"{settings.storage.signatures_path}/{user_id}-{uuid.uuid4()}.png"

        # Upload to S3
        try:
            # Upload with appropriate content type
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=signature_data,
                ContentType="image/png",
            )

            logger.info(f"Uploaded signature to AWS S3: {object_key}")

            # Return the object key for storage in the database
            return object_key
        except Exception as e:
            logger.error(f"Error uploading signature to S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload signature: {str(e)}",
            )

    async def save_resume_pdf(self, pdf_data: bytes, resume_id: str) -> str:
        """Upload a resume PDF to AWS S3."""
        # Validate PDF
        is_valid, error_message = await self.validate_pdf(pdf_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
            )

        # Format: resumes/resume_id-uuid.pdf
        object_key = f"{settings.storage.resumes_path}/{resume_id}-{uuid.uuid4()}.pdf"

        # Upload to S3
        try:
            # Upload with appropriate content type
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=pdf_data,
                ContentType="application/pdf",
            )

            logger.info(f"Uploaded resume PDF to AWS S3: {object_key}")

            # Return the object key for storage in the database
            return object_key
        except Exception as e:
            logger.error(f"Error uploading resume PDF to S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload PDF: {str(e)}",
            )

    async def save_cover_letter_pdf(self, pdf_data: bytes, cover_letter_id: str) -> str:
        """Upload a cover letter PDF to AWS S3."""
        # Validate PDF
        is_valid, error_message = await self.validate_pdf(pdf_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
            )

        # Format: cover-letters/cover_letter_id-uuid.pdf
        object_key = f"{settings.storage.cover_letters_path}/{cover_letter_id}-{uuid.uuid4()}.pdf"

        # Upload to S3
        try:
            # Upload with appropriate content type
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=pdf_data,
                ContentType="application/pdf",
            )

            logger.info(f"Uploaded cover letter PDF to AWS S3: {object_key}")

            # Return the object key for storage in the database
            return object_key
        except Exception as e:
            logger.error(f"Error uploading cover letter PDF to S3: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload PDF: {str(e)}",
            )

    async def delete_file(self, object_key: str) -> bool:
        """Delete a file from AWS S3."""
        if not object_key:
            return False

        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"Deleted file from AWS S3: {object_key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting from AWS S3: {str(e)}")
            return False

    def get_url(self, object_key: Optional[str]) -> Optional[str]:
        """Get the URL for an AWS S3 object."""
        if not object_key:
            return None

        # If CloudFront is enabled, use CloudFront URL
        if self.cloudfront_enabled and self.cloudfront_domain:
            if self.cloudfront_signer and settings.storage.cloudfront_key_pair_id:
                # Generate a signed URL
                expiry_time = int(time.time() + settings.storage.cloudfront_url_expiry)
                cloudfront_url = f"https://{self.cloudfront_domain}/{object_key}"

                try:
                    signed_url = self.cloudfront_signer.generate_presigned_url(
                        cloudfront_url, date_less_than=expiry_time
                    )
                    return signed_url
                except Exception as e:
                    logger.error(f"Failed to generate CloudFront signed URL: {str(e)}")

            # Return unsigned CloudFront URL
            return f"https://{self.cloudfront_domain}/{object_key}"

        # If presigned URLs are enabled, generate a presigned S3 URL
        if settings.storage.aws_use_presigned_urls:
            try:
                presigned_url = self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": object_key},
                    ExpiresIn=settings.storage.aws_presigned_url_expiry,
                )
                return presigned_url
            except Exception as e:
                logger.error(f"Error generating pre-signed URL: {str(e)}")
                # Fall back to direct URL (may not work if bucket is private)

        # Return direct S3 URL
        return f"https://{self.bucket}.s3.{settings.storage.aws_region}.amazonaws.com/{object_key}"


def get_storage_provider() -> StorageProvider:
    """
    Get the appropriate storage provider based on settings.

    Returns:
        StorageProvider: Storage provider instance
    """
    provider_type = settings.storage.provider.lower()

    if provider_type == "aws_s3":
        # Check if AWS S3 settings are configured
        if not settings.storage.aws_access_key or not settings.storage.aws_secret_key:
            logger.warning(
                "AWS S3 credentials not configured. Falling back to local storage."
            )
            return LocalStorageProvider()
        return AWSS3StorageProvider()

    # Default to local storage
    return LocalStorageProvider()
