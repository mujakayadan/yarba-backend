"""Authentication service for user management using Firebase."""

import re
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
    NotFoundException,
    UnauthorizedException,
)
from core.models.user import User
from core.repositories.user_repository import UserRepository

settings = Settings()


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
    ) -> Dict[str, Any]:
        """
        Register a new user with Firebase Authentication and return data for login.
        Username will be auto-generated from email.
        Firebase display_name will be auto-generated from email prefix.

        Args:
            email: User email
            password: User password

        Returns:
            Dict: User data and access token

        Raises:
            BadRequestException: If user already exists or Firebase registration fails
        """
        self.logger.info(
            f"[AuthService.register] Attempting to register user. Email: {email}"
        )

        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            self.logger.warning(
                f"Registration failed: Email {email} already registered"
            )
            raise BadRequestException("Email already registered")

        try:
            self.logger.info(
                f"[AuthService.register] About to call FirebaseAuth.create_user for email: {email}"
            )
            firebase_display_name = email.split("@")[0]
            self.logger.info(
                f"[AuthService.register] Using display_name for Firebase: {firebase_display_name}"
            )

            firebase_user_data = await FirebaseAuth.create_user(
                email=email,
                password=password,
                display_name=firebase_display_name,
            )
            firebase_user_uid = firebase_user_data.get("uid")

            generated_internal_username = email.split("@")[0].lower().replace(" ", "_")
            self.logger.info(
                f"[AuthService.register] Generated base internal username: {generated_internal_username} for email: {email}"
            )

            existing_username_obj = await self.user_repository.get_by_username(
                generated_internal_username
            )
            if existing_username_obj:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                final_username_for_db = f"{generated_internal_username}_{timestamp}"
                self.logger.info(
                    f"[AuthService.register] Generated internal username conflicted, new unique username: {final_username_for_db} for email: {email}"
                )
            else:
                final_username_for_db = generated_internal_username

            # Ensure username is not None before creating User model instance (should not happen)
            if final_username_for_db is None:
                self.logger.error(
                    f"[AuthService.register] Critical error: final_username_for_db is None before User model creation for email: {email}"
                )
                raise BadRequestException(
                    "Internal server error during username assignment."
                )

            self.logger.info(
                f"[AuthService.register] Preparing to create local DB user. Email: {email}, Final Username: {final_username_for_db}, Firebase UID: {firebase_user_uid}"
            )

            user = User(
                email=email,
                username=final_username_for_db,
                is_active=True,
                email_verified=False,
                firebase_uid=firebase_user_uid,
                auth_provider="firebase.password",
            )

            created_user = await self.user_repository.create(user)
            self.logger.info(f"User registered with Firebase: {email}")

            self.logger.info(
                f"[AuthService.register] Attempting to send verification email for: {email}"
            )
            await self.send_verification_email(email)
            self.logger.info(
                f"[AuthService.register] Verification email process completed for: {email}"
            )

            access_token = self.create_access_token(data={"sub": created_user.email})
            self.logger.info(
                f"[AuthService.register] Access token generated for new user: {email}"
            )

            # Return data similar to login_with_firebase response
            return {
                "user": {
                    "id": str(created_user.id),
                    "email": created_user.email,
                    "username": created_user.username,
                    "email_verified": created_user.email_verified,  # Will be False initially
                    "is_active": created_user.is_active,
                    "is_superuser": created_user.is_superuser,
                    "auth_provider": created_user.auth_provider,
                    # Add other fields if they are part of your User model and needed by FirebaseAuthResponse
                },
                "access_token": access_token,
                "token_type": "bearer",
                "is_new_user": created_user.is_new_user,
                "current_setup_step": created_user.current_setup_step,
            }

        except Exception as e:
            self.logger.error(
                f"Registration process error for email {email}: {str(e)}", exc_info=True
            )
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

            if not re.match(
                r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$", id_token
            ):
                self.logger.warning(f"Token format does not match expected JWT pattern")
                raise UnauthorizedException("Invalid token format")

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

            user = await self.user_repository.get_by_email(email)

            if not user:
                self.logger.info(
                    f"First-time Firebase login for {email}, creating user record"
                )
                try:
                    firebase_user = await FirebaseAuth.get_user(uid)
                    username = firebase_user.get("display_name") or email.split("@")[0]
                    username = username.lower().replace(" ", "_")

                    existing_user_with_username = (
                        await self.user_repository.get_by_username(username)
                    )
                    if existing_user_with_username:
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        username = f"{username}_{timestamp}"

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
                self.logger.info(f"Updating Firebase UID for user: {email}")
                user.firebase_uid = uid
                user = await self.user_repository.update(user.id, user)

            await self.user_repository.update_last_login(user.id)
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
                    # Expose all User model fields that are safe and useful for the frontend
                    "last_login": user.last_login,
                    "created_at": user.created_at,
                    "subscription_status": user.subscription_status,
                },
                "access_token": access_token,
                "token_type": "bearer",
                "is_new_user": user.is_new_user,
                "current_setup_step": user.current_setup_step,
            }

        except Exception as e:
            self.logger.error(f"Firebase login error: {str(e)}", exc_info=True)
            raise UnauthorizedException(f"Firebase authentication failed: {str(e)}")

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
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

            user = await self.user_repository.get_by_email(email)
            if not user or not user.firebase_uid:
                self.logger.error(f"User not found or missing Firebase UID: {email}")
                raise Exception("User not found or not a Firebase user")

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

    async def update_user(
        self, user_id: PydanticObjectId, update_data: Dict[str, Any]
    ) -> User:
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
        self, user_id: PydanticObjectId, update_data: Dict[str, Any]
    ) -> User:
        """
        Update user data in both Firebase and local database.

        Args:
            user_id: User ID in the local database (PydanticObjectId)
            update_data: Dictionary of fields to update (e.g., {"display_name": "New Name"})

        Returns:
            User: Updated user object from the local database

        Raises:
            NotFoundException: If user not found in local database
            HTTPException: If Firebase update fails
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(
                f"User not found with ID: {user_id} for Firebase update"
            )
            raise NotFoundException("User not found")

        firebase_update_payload = {}
        if "email" in update_data:
            firebase_update_payload["email"] = update_data["email"]
        if "password" in update_data:
            firebase_update_payload["password"] = update_data["password"]
        if "display_name" in update_data:
            firebase_update_payload["display_name"] = update_data["display_name"]
        if "email_verified" in update_data:
            firebase_update_payload["email_verified"] = update_data["email_verified"]

        if firebase_update_payload:
            try:
                await FirebaseAuth.update_user(
                    user.firebase_uid, **firebase_update_payload
                )
                self.logger.info(f"Successfully updated user {user.email} in Firebase.")
            except Exception as e:
                self.logger.error(
                    f"Failed to update user {user.email} in Firebase: {str(e)}",
                    exc_info=True,
                )
                # Depending on policy, you might want to raise an exception or just log
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Firebase update failed: {str(e)}",
                )

        # Only update fields that are part of the User model
        allowed_local_fields = User.model_fields.keys()
        local_update_data = {
            k: v for k, v in update_data.items() if k in allowed_local_fields
        }

        if local_update_data:
            updated_user = await self.user_repository.update(user.id, local_update_data)  # type: ignore
            self.logger.info(f"Successfully updated user {user.email} in local DB.")
            return updated_user

        # Return original user if no local updates were made but Firebase might have been
        return user

    async def update_user_setup_progress(
        self,
        user_id: PydanticObjectId,
        current_setup_step: Optional[int],
        setup_completed: Optional[bool],
    ) -> User:
        """
        Update the user's setup progress.

        Args:
            user_id: The ID of the user to update.
            current_setup_step: The current setup step number.
            setup_completed: Boolean indicating if the setup is fully completed.

        Returns:
            The updated User object.

        Raises:
            NotFoundException: If the user is not found.
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(
                f"User not found with ID: {user_id} for setup progress update"
            )
            raise NotFoundException("User not found")

        update_data = {}
        if current_setup_step is not None:
            user.current_setup_step = current_setup_step
            update_data["current_setup_step"] = current_setup_step

        if setup_completed is not None:
            user.is_new_user = (
                not setup_completed
            )  # if setup_completed is True, is_new_user becomes False
            update_data["is_new_user"] = user.is_new_user
            if setup_completed:
                # Optionally, if setup is completed, we can set step to a final/non-relevant value like 0 or max_step + 1
                user.current_setup_step = 0  # Or some other indicator of completion
                update_data["current_setup_step"] = 0

        if not update_data:
            return user

        # Instead of passing the dictionary directly, save the updated user object
        await user.save()
        self.logger.info(
            f"Updated setup progress for user {user_id}: step {user.current_setup_step}, new_user {user.is_new_user}"
        )
        return user

    async def verify_token(self, token: str) -> Tuple[Dict[str, Any], User]:
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
        if (
            not updated_user
        ):  # Should not happen if get_by_id succeeded and update is on Pydantic model
            self.logger.error(f"Failed to deactivate user: {user_id}")
            # This path might indicate an issue with the .update method or transactionality
            # For now, keeping NotFoundException as per original logic if update returns None
            raise NotFoundException("User not found or failed to update")

        self.logger.info(f"User deactivated: {user_id}")
        return updated_user
