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
    def debug_environment(cls):
        """Debug helper to print environment variables.

        This method directly checks environment variables to help diagnose issues.
        """
        # Direct environment variable access
        firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
        firebase_private_key = (
            "PRESENT" if os.environ.get("FIREBASE_PRIVATE_KEY") else "MISSING"
        )
        firebase_client_email = os.environ.get("FIREBASE_CLIENT_EMAIL", "")

        # Settings based access
        settings_project_id = settings.auth.firebase_project_id
        settings_private_key = (
            "PRESENT" if settings.auth.firebase_private_key else "MISSING"
        )
        settings_client_email = settings.auth.firebase_client_email

        # MongoDB settings
        mongo_uri_env = os.environ.get("MONGODB_URI", "")
        mongo_uri_settings = settings.database.url

        logger.debug("=== ENVIRONMENT DEBUG INFO ===")
        logger.debug(f"Env - FIREBASE_PROJECT_ID: {firebase_project_id}")
        logger.debug(f"Env - FIREBASE_PRIVATE_KEY: {firebase_private_key}")
        logger.debug(f"Env - FIREBASE_CLIENT_EMAIL: {firebase_client_email}")
        logger.debug(f"Settings - firebase_project_id: {settings_project_id}")
        logger.debug(f"Settings - firebase_private_key: {settings_private_key}")
        logger.debug(f"Settings - firebase_client_email: {settings_client_email}")
        logger.debug(f"Env - MONGODB_URI: {mongo_uri_env}")
        logger.debug(f"Settings - database.url: {mongo_uri_settings}")
        logger.debug("=== END DEBUG INFO ===")

    @classmethod
    def initialize(cls, service_account_path: Optional[str] = None) -> bool:
        """Initialize Firebase Admin SDK.

        Args:
            service_account_path: Path to Firebase service account credentials file.
                If not provided, will use credentials from environment variables.

        Returns:
            bool: True if initialized successfully, False otherwise.
        """
        if cls._initialized:
            logger.info("Firebase already initialized")
            return True

        # Run debug to help diagnose issues
        cls.debug_environment()

        try:
            # Use credentials from settings.auth which are loaded from environment variables
            cred_dict = settings.auth.get_firebase_credentials_dict()

            # Debug info - what credentials do we have?
            logger.debug(
                f"Firebase project_id loaded: {bool(settings.auth.firebase_project_id)}"
            )
            logger.debug(
                f"Firebase private_key loaded: {bool(settings.auth.firebase_private_key)}"
            )
            logger.debug(
                f"Firebase client_email loaded: {bool(settings.auth.firebase_client_email)}"
            )

            if (
                cred_dict.get("project_id")
                and cred_dict.get("private_key")
                and cred_dict.get("client_email")
            ):
                logger.info(
                    "Initializing Firebase Admin SDK with credentials from environment variables"
                )

                # Log success without sensitive details
                logger.debug(
                    f"Created credential dict with project_id: {cred_dict.get('project_id')}"
                )

                # Initialize Firebase with the constructed credentials
                cred = credentials.Certificate(cred_dict)
                cls._app = firebase_admin.initialize_app(cred)
                cls._initialized = True
                logger.info(
                    "Successfully initialized Firebase Admin SDK from environment variables"
                )
                return True

            # Default credentials (useful for development)
            logger.warning("No valid credentials found. Using default credentials.")
            logger.warning(
                f"Missing credentials: project_id={not bool(cred_dict.get('project_id'))}, private_key={not bool(cred_dict.get('private_key'))}, client_email={not bool(cred_dict.get('client_email'))}"
            )
            cls._app = firebase_admin.initialize_app()
            cls._initialized = True
            logger.info(
                "Successfully initialized Firebase Admin SDK with default credentials"
            )
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
            Exception: If operation fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            action_code_settings = None
            if settings.auth.api_base_url:
                action_code_settings = auth.ActionCodeSettings(
                    url=f"{settings.auth.api_base_url}{settings.auth.password_reset_path}",
                    handle_code_in_app=True,
                )

            link = auth.generate_password_reset_link(
                email, action_code_settings=action_code_settings
            )
            return link
        except Exception as e:
            logger.error(f"Failed to generate password reset link: {str(e)}")
            raise

    @classmethod
    async def get_user_by_email(cls, email: str) -> Dict[str, Any]:
        """Get Firebase user by email.

        Args:
            email: Firebase user email

        Returns:
            Dict: Firebase user record as dict

        Raises:
            Exception: If user retrieval fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            user = auth.get_user_by_email(email)
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "email_verified": user.email_verified,
                "disabled": user.disabled,
                "phone_number": user.phone_number,
            }
        except Exception as e:
            logger.error(f"Failed to get Firebase user by email: {str(e)}")
            raise

    @classmethod
    async def create_custom_token(cls, uid: str) -> str:
        """Create a custom Firebase token for a user.

        Args:
            uid: Firebase user UID

        Returns:
            str: Custom Firebase token

        Raises:
            Exception: If token creation fails
        """
        if not cls._initialized:
            if not cls.initialize():
                raise Exception("Firebase could not be initialized")

        try:
            custom_token = auth.create_custom_token(uid)
            return (
                custom_token.decode("utf-8")
                if isinstance(custom_token, bytes)
                else custom_token
            )
        except Exception as e:
            logger.error(f"Failed to create custom Firebase token: {str(e)}")
            raise

    @classmethod
    async def exchange_custom_token_for_id_token(cls, custom_token: str) -> str:
        """Exchange a custom token for an ID token using Firebase REST API.

        Note: This requires HTTP requests to Firebase Auth REST API.

        Args:
            custom_token: Custom Firebase token

        Returns:
            str: Firebase ID token

        Raises:
            Exception: If token exchange fails
        """
        import aiohttp

        try:
            # Get the API key from settings
            api_key = settings.auth.firebase_api_key
            if not api_key:
                raise ValueError(
                    "Firebase API key not found in environment variables or settings"
                )

            # Exchange custom token for ID token using Firebase Auth REST API
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json={"token": custom_token, "returnSecureToken": True}
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise Exception(f"Firebase API error: {error_data}")

                    data = await response.json()
                    return data.get("idToken")
        except Exception as e:
            logger.error(f"Failed to exchange custom token for ID token: {str(e)}")
            raise

    @classmethod
    async def sign_in_with_email_password(
        cls, email: str, password: str
    ) -> Dict[str, Any]:
        """Sign in with email and password using Firebase REST API.

        Note: This requires HTTP requests to Firebase Auth REST API.

        Args:
            email: User email
            password: User password

        Returns:
            Dict: Firebase authentication response including ID token

        Raises:
            Exception: If authentication fails
        """
        import aiohttp

        try:
            # Get the API key from settings
            api_key = (
                os.environ.get("FIREBASE_API_KEY") or settings.auth.firebase_api_key
            )
            if not api_key:
                raise ValueError(
                    "Firebase API key not found in environment variables or settings"
                )

            # Sign in with email/password using Firebase Auth REST API
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "email": email,
                        "password": password,
                        "returnSecureToken": True,
                    },
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise Exception(f"Firebase API error: {error_data}")

                    return await response.json()
        except Exception as e:
            logger.error(f"Failed to sign in with email and password: {str(e)}")
            raise
