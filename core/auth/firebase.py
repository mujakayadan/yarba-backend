"""Firebase authentication integration module.

This module provides functions and classes for integrating Firebase Authentication
with the application.
"""

import os
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import auth, credentials
from pydantic import EmailStr

from config.logging_config import get_logger
from config.settings import Settings
from core.utils.url_helpers import get_api_url

settings = Settings()
logger = get_logger(__name__)


class FirebaseAuth:
    """Firebase authentication wrapper class."""

    _initialized = False
    _app = None

    @classmethod
    def initialize(cls, service_account_path: Optional[str] = None) -> bool:
        """Initialize Firebase Admin SDK.

        Args:
            service_account_path: Path to Firebase service account credentials file.
                If not provided, will use FIREBASE_CREDENTIALS environment variable.

        Returns:
            bool: True if initialized successfully, False otherwise.
        """
        if cls._initialized:
            logger.info("Firebase already initialized")
            return True

        try:
            # Get credentials path from args or environment
            cred_path = service_account_path or os.environ.get(
                "FIREBASE_CREDENTIALS", settings.auth.firebase_credentials_path
            )

            logger.info(
                f"Initializing Firebase Admin SDK with credentials from {cred_path}"
            )

            # Initialize Firebase Admin
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                cls._app = firebase_admin.initialize_app(cred)
            else:
                # Default credentials (useful for development)
                logger.warning("Credentials file not found. Using default credentials.")
                cls._app = firebase_admin.initialize_app()

            cls._initialized = True
            logger.info("Successfully initialized Firebase Admin SDK")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            import traceback

            logger.error(f"Error details: {traceback.format_exc()}")
            return False

    @classmethod
    async def create_user(
        cls,
        email: EmailStr,
        password: str,
        display_name: str,
        phone_number: Optional[str] = None,
        email_verified: bool = False,
        disabled: bool = False,
    ) -> Dict[str, Any]:
        """Create a new Firebase user.

        Args:
            email: User email
            password: User password
            display_name: User display name
            phone_number: User phone number (optional)
            email_verified: Whether the email is verified (default: False)
            disabled: Whether the user is disabled (default: False)

        Returns:
            Dict: Firebase user record as dict

        Raises:
            Exception: If user creation fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            user = auth.create_user(
                email=email,
                email_verified=email_verified,
                phone_number=phone_number,
                password=password,
                display_name=display_name,
                disabled=disabled,
            )

            logger.info(f"Successfully created Firebase user: {user.uid}")
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "disabled": user.disabled,
                "phone_number": user.phone_number,
            }

        except Exception as e:
            logger.error(f"Failed to create Firebase user: {str(e)}")
            raise

    @classmethod
    async def verify_token(cls, id_token: str) -> Dict[str, Any]:
        """Verify Firebase ID token.

        Args:
            id_token: Firebase ID token

        Returns:
            Dict: Token claims if valid

        Raises:
            Exception: If token verification fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            # Log token info for debugging (only first 10 chars for security)
            token_preview = id_token[:10] + "..." if len(id_token) > 10 else id_token
            logger.debug(f"Attempting to verify Firebase token: {token_preview}")

            # Try to decode the token to check its structure
            import jwt as pyjwt

            try:
                # Just decode without verification to see the structure
                header = pyjwt.get_unverified_header(id_token)
                logger.debug(f"Token header: {header}")
            except Exception as decode_error:
                logger.warning(f"Failed to decode token header: {str(decode_error)}")

            # Now verify with Firebase
            decoded_token = auth.verify_id_token(id_token)
            logger.debug(
                f"Successfully verified token for user: {decoded_token.get('uid')}"
            )
            return decoded_token

        except Exception as e:
            logger.error(f"Failed to verify Firebase token: {str(e)}")
            raise

    @classmethod
    async def get_user(cls, uid: str) -> Dict[str, Any]:
        """Get Firebase user by UID.

        Args:
            uid: Firebase user UID

        Returns:
            Dict: Firebase user record as dict

        Raises:
            Exception: If user retrieval fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            user = auth.get_user(uid)
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "disabled": user.disabled,
                "phone_number": user.phone_number,
            }

        except Exception as e:
            logger.error(f"Failed to get Firebase user: {str(e)}")
            raise

    @classmethod
    async def update_user(cls, uid: str, **kwargs) -> Dict[str, Any]:
        """Update Firebase user.

        Args:
            uid: Firebase user UID
            **kwargs: User properties to update

        Returns:
            Dict: Updated Firebase user record as dict

        Raises:
            Exception: If user update fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            user = auth.update_user(uid, **kwargs)
            logger.info(f"Successfully updated Firebase user: {user.uid}")
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "disabled": user.disabled,
                "phone_number": user.phone_number,
            }

        except Exception as e:
            logger.error(f"Failed to update Firebase user: {str(e)}")
            raise

    @classmethod
    async def delete_user(cls, uid: str) -> bool:
        """Delete Firebase user.

        Args:
            uid: Firebase user UID

        Returns:
            bool: True if deleted successfully

        Raises:
            Exception: If user deletion fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            auth.delete_user(uid)
            logger.info(f"Successfully deleted Firebase user: {uid}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete Firebase user: {str(e)}")
            raise

    @classmethod
    async def generate_email_verification_link(cls, email: str) -> str:
        """Generate email verification link.

        Args:
            email: User email

        Returns:
            str: Email verification link

        Raises:
            Exception: If link generation fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            action_code_settings = auth.ActionCodeSettings(
                url=get_api_url(settings.auth.email_verification_path)
            )
            link = auth.generate_email_verification_link(email, action_code_settings)
            logger.info(f"Generated email verification link for: {email}")
            return link

        except Exception as e:
            logger.error(f"Failed to generate email verification link: {str(e)}")
            raise

    @classmethod
    async def generate_password_reset_link(cls, email: str) -> str:
        """Generate password reset link.

        Args:
            email: User email

        Returns:
            str: Password reset link

        Raises:
            Exception: If link generation fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            action_code_settings = auth.ActionCodeSettings(
                url=get_api_url(settings.auth.password_reset_path)
            )
            link = auth.generate_password_reset_link(email, action_code_settings)
            logger.info(f"Generated password reset link for: {email}")
            return link

        except Exception as e:
            logger.error(f"Failed to generate password reset link: {str(e)}")
            raise
