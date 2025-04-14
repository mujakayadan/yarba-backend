"""Authentication service for user management using Firebase."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import EmailStr

from config.logging_config import get_logger
from config.settings import Settings
from core.auth.firebase import FirebaseAuth
from core.exceptions.base import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from core.models.user import User
from core.repositories.user_repository import UserRepository

settings = Settings()
logger = get_logger(__name__)


class AuthService:
    """Service for Firebase authentication and user operations."""

    def __init__(self, user_repository: Optional[UserRepository] = None):
        """
        Initialize the authentication service.

        Args:
            user_repository: Repository for accessing user data
        """
        self.user_repository = user_repository or UserRepository()
        self.logger = get_logger(self.__class__.__name__)

    async def register_with_firebase(
        self,
        email: EmailStr,
        password: str,
        full_name: str,
        username: Optional[str] = None,
    ) -> User:
        """
        Register a new user with Firebase Authentication.

        Args:
            email: User email
            password: User password
            full_name: User full name
            username: Optional username, will use full_name or generate from email if not provided

        Returns:
            User: Created user

        Raises:
            BadRequestException: If user already exists or Firebase registration fails
        """
        # Check if user already exists in our database
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            self.logger.warning(
                f"Registration failed: Email {email} already registered"
            )
            raise BadRequestException("Email already registered")

        try:
            # Create user in Firebase
            firebase_user = await FirebaseAuth.create_user(
                email=email,
                password=password,
                display_name=full_name,
            )

            # Use provided username or generate one
            if not username:
                username = full_name.lower().replace(" ", "_")

                # Check if username exists and add suffix if needed
                existing_username = await self.user_repository.get_by_username(username)
                if existing_username:
                    from datetime import datetime

                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    username = f"{username}_{timestamp}"

            # Create user in our database
            user = User(
                email=email,
                username=username,
                is_active=True,
                email_verified=False,
                firebase_uid=firebase_user["uid"],
                auth_provider="firebase.password",
            )

            created_user = await self.user_repository.create(user)
            self.logger.info(f"User registered with Firebase: {email}")

            # Generate and send verification email
            await self.send_verification_email(email)

            return created_user

        except Exception as e:
            self.logger.error(f"Firebase registration error: {str(e)}")
            raise BadRequestException(f"Firebase registration failed: {str(e)}")

    async def login_with_firebase(self, id_token: str) -> Dict[str, Any]:
        """
        Login with Firebase ID token.

        Args:
            id_token: Firebase ID token

        Returns:
            Dict: User data and access token

        Raises:
            UnauthorizedException: If token verification fails
        """
        try:
            self.logger.debug(
                f"Processing Firebase login with token length: {len(id_token)}"
            )

            # Check if the token looks like a valid JWT
            import re

            if not re.match(
                r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$", id_token
            ):
                self.logger.warning(f"Token format does not match expected JWT pattern")
                raise UnauthorizedException("Invalid token format")

            # Verify Firebase token
            token_data = await FirebaseAuth.verify_token(id_token)
            uid = token_data.get("uid")
            email = token_data.get("email")

            if not uid or not email:
                self.logger.warning(
                    f"Firebase token missing required claims (uid or email)"
                )
                raise UnauthorizedException(
                    "Invalid Firebase token: missing required claims"
                )

            # Check if user exists in our database
            user = await self.user_repository.get_by_email(email)

            if not user:
                # Create a new user record if this is their first login
                self.logger.info(
                    f"First-time Firebase login for {email}, creating user record"
                )
                try:
                    firebase_user = await FirebaseAuth.get_user(uid)
                    # Generate a valid username from display name or email
                    username = firebase_user.get("display_name") or email.split("@")[0]
                    # Convert username to valid format (lowercase, no spaces)
                    username = username.lower().replace(" ", "_")

                    # Ensure username is unique by checking database
                    existing_user_with_username = (
                        await self.user_repository.get_by_username(username)
                    )
                    if existing_user_with_username:
                        # Add a timestamp to make username unique
                        from datetime import datetime

                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        username = f"{username}_{timestamp}"

                    # Determine the authentication provider from the token data
                    provider_data = token_data.get("firebase", {}).get(
                        "sign_in_provider", ""
                    )
                    auth_provider = (
                        f"firebase.{provider_data.split('.')[0]}"
                        if provider_data
                        else "firebase.password"
                    )

                    user = User(
                        email=email,
                        username=username,
                        is_active=True,
                        email_verified=firebase_user.get("email_verified", False),
                        firebase_uid=uid,
                        auth_provider=auth_provider,
                    )
                    user = await self.user_repository.create(user)
                    self.logger.info(f"Created new user from Firebase login: {email}")
                except Exception as user_create_error:
                    self.logger.error(
                        f"Failed to create user from Firebase auth: {str(user_create_error)}"
                    )
                    raise UnauthorizedException(
                        f"User creation failed: {str(user_create_error)}"
                    )
            elif user.firebase_uid != uid:
                # Update Firebase UID if it's different
                self.logger.info(f"Updating Firebase UID for user: {email}")
                user.firebase_uid = uid
                user = await self.user_repository.update(user.id, user)

            # Update last login timestamp
            await self.user_repository.update_last_login(user.id)

            # Generate JWT token for our API
            access_token = self.create_access_token(data={"sub": user.email})

            self.logger.info(f"Firebase login successful for {email}")

            return {
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "email_verified": user.email_verified,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "auth_provider": user.auth_provider,
                },
                "access_token": access_token,
                "token_type": "bearer",
            }

        except Exception as e:
            self.logger.error(f"Firebase login error: {str(e)}", exc_info=True)
            raise UnauthorizedException(f"Firebase authentication failed: {str(e)}")

    def create_access_token(
        self, data: Dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Token data
            expires_delta: Token expiration time

        Returns:
            str: JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.auth.jwt_access_token_expire_minutes
            )

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithm=settings.auth.jwt_algorithm,
        )

        return encoded_jwt

    async def send_verification_email(self, email: EmailStr) -> bool:
        """
        Send a verification email using Firebase.

        Args:
            email: User email

        Returns:
            bool: True if email sent successfully

        Raises:
            Exception: If email sending fails
        """
        try:
            verification_link = await FirebaseAuth.generate_email_verification_link(
                email
            )
            # Here you would typically send the email with the verification_link
            # For now, we'll just log it
            self.logger.info(f"Verification link for {email}: {verification_link}")
            # In a real application, you would use an email service to send this link
            return True
        except Exception as e:
            self.logger.error(f"Failed to send verification email: {str(e)}")
            raise

    async def send_password_reset_email(self, email: EmailStr) -> bool:
        """
        Send a password reset email using Firebase.

        Args:
            email: User email

        Returns:
            bool: True if email sent successfully

        Raises:
            Exception: If email sending fails
        """
        try:
            reset_link = await FirebaseAuth.generate_password_reset_link(email)
            # Here you would typically send the email with the reset_link
            # For now, we'll just log it
            self.logger.info(f"Password reset link for {email}: {reset_link}")
            # In a real application, you would use an email service to send this link
            return True
        except Exception as e:
            self.logger.error(f"Failed to send password reset email: {str(e)}")
            raise

    async def change_firebase_password(
        self, email: EmailStr, current_password: str, new_password: str
    ) -> bool:
        """
        Change a Firebase user's password.

        Args:
            email: User email
            current_password: Current password
            new_password: New password

        Returns:
            bool: True if password change was successful

        Raises:
            Exception: If password change fails
        """
        try:
            # First, validate the current password by trying to sign in
            # This is a Firebase requirement for security
            await FirebaseAuth.sign_in_with_email_password(email, current_password)

            # If successful, update the password
            user = await self.user_repository.get_by_email(email)
            if not user or not user.firebase_uid:
                self.logger.error(f"User not found or missing Firebase UID: {email}")
                raise Exception("User not found or not a Firebase user")

            # Update the password in Firebase
            await FirebaseAuth.update_user(user.firebase_uid, password=new_password)

            self.logger.info(f"Password changed successfully for user: {email}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to change Firebase password: {str(e)}")
            raise

    async def get_user_by_id(self, user_id: PydanticObjectId) -> User:
        """
        Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User: User

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        return user

    async def get_user_by_email(self, email: EmailStr) -> User:
        """
        Get a user by email.

        Args:
            email: User email

        Returns:
            User: User

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_email(email)
        if not user:
            self.logger.warning(f"User not found: {email}")
            raise NotFoundException("User not found")

        return user

    async def update_user(self, user_id: PydanticObjectId, update_data: Dict) -> User:
        """
        Update a user.

        Args:
            user_id: User ID
            update_data: Data to update

        Returns:
            User: Updated user

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(user_id)

        for key, value in update_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.now(timezone.utc)

        try:
            await user.save()
            self.logger.info(f"User updated: {user_id}")
            return user
        except Exception as e:
            self.logger.error(f"Failed to update user: {str(e)}")
            raise NotFoundException("User not found")

    async def update_user_with_firebase(
        self, user_id: str, update_data: Dict[str, Any]
    ) -> User:
        """
        Update a user in both Firebase and our database.

        Args:
            user_id: User ID in our database
            update_data: Data to update

        Returns:
            User: Updated user

        Raises:
            Exception: If update fails
        """
        try:
            # Get user from our database
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise BadRequestException("User not found")

            # If this is a Firebase user, update in Firebase
            if user.firebase_uid:
                firebase_update = {}

                if "email" in update_data:
                    firebase_update["email"] = update_data["email"]

                if "username" in update_data:
                    firebase_update["display_name"] = update_data["username"]

                if firebase_update:
                    await FirebaseAuth.update_user(user.firebase_uid, **firebase_update)

            # Update in our database
            updated_user = await self.user_repository.update_by_id(user_id, update_data)
            return updated_user

        except Exception as e:
            self.logger.error(f"User update error: {str(e)}")
            raise

    async def verify_token(self, token: str) -> Tuple[Dict, User]:
        """
        Verify a JWT token and get the user.

        Args:
            token: JWT token

        Returns:
            Tuple[Dict, User]: Token payload and user

        Raises:
            UnauthorizedException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.auth.jwt_secret_key.get_secret_value(),
                algorithms=[settings.auth.jwt_algorithm],
            )

            email = payload.get("sub")
            if email is None:
                self.logger.warning("Token verification failed: Missing subject claim")
                raise UnauthorizedException("Invalid token")

            user = await self.get_user_by_email(email)
            return payload, user

        except JWTError as e:
            self.logger.warning(f"Token verification failed: {str(e)}")
            raise UnauthorizedException("Invalid token")

    async def deactivate_user(self, user_id: PydanticObjectId) -> User:
        """
        Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            User: Deactivated user

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(user_id)

        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)

        updated_user = await self.user_repository.update(user_id, user)
        if not updated_user:
            self.logger.error(f"Failed to deactivate user: {user_id}")
            raise NotFoundException("User not found")

        self.logger.info(f"User deactivated: {user_id}")
        return updated_user
