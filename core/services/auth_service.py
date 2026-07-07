"""Authentication service for user management using Firebase."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from beanie import PydanticObjectId
from fastapi import HTTPException, status
from firebase_admin.auth import EmailAlreadyExistsError
from jwt.exceptions import PyJWTError as JWTError
from pydantic import EmailStr

from config.logging_config import get_logger
from config.settings import Settings
from core.auth.error_codes import (
    ACCOUNT_EXISTS_USE_LOGIN,
    EMAIL_ALREADY_REGISTERED,
    FIREBASE_REGISTRATION_FAILED,
    INVALID_CREDENTIALS,
)
from core.auth.firebase import FirebaseAuth
from core.exceptions.base import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from core.models.user import User
from core.repositories.user_repository import UserRepository
from core.services.email_clients.resend_client import ResendClient
from core.utils.object_id import require_object_id

settings = Settings()


class AuthService:
    """Service for Firebase authentication and user operations."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        resend_client: ResendClient | None = None,
    ):
        """Initialize the authentication service.

        Args:
            user_repository: Repository for accessing user data
            resend_client: Optional Resend client for auth-related emails
        """
        self.user_repository = user_repository or UserRepository()
        self.resend_client = resend_client
        self.logger = get_logger(self.__class__.__name__)

    async def _resolve_unique_username(self, base_username: str) -> str:
        """Return a username that is not already taken in MongoDB."""
        username = base_username.lower().replace(" ", "_")
        existing = await self.user_repository.get_by_username(username)
        if existing:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"{username}_{timestamp}"
        return username

    async def _create_local_user_from_firebase(
        self,
        *,
        email: EmailStr,
        firebase_uid: str,
        email_verified: bool,
        auth_provider: str,
        display_name: str | None = None,
    ) -> User:
        """Create a MongoDB user record for an existing Firebase account."""
        base_username = display_name or email.split("@")[0]
        username = await self._resolve_unique_username(base_username)
        user = User(
            email=email,
            username=username,
            is_active=True,
            email_verified=email_verified,
            firebase_uid=firebase_uid,
            auth_provider=auth_provider,
        )
        return await self.user_repository.create(user)

    def _build_registration_response(
        self,
        user: User,
        *,
        registration_resumed: bool = False,
    ) -> dict[str, Any]:
        """Build the register/login response payload."""
        access_token = self.create_access_token(data={"sub": user.email})
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
            "is_new_user": user.is_new_user,
            "current_setup_step": user.current_setup_step,
            "registration_resumed": registration_resumed,
        }

    async def _sync_orphan_firebase_user(
        self,
        email: EmailStr,
        password: str,
    ) -> dict[str, Any]:
        """Link an existing Firebase account to a new MongoDB user after password verification."""
        try:
            await FirebaseAuth.sign_in_with_email_password(email, password)
        except Exception:
            firebase_user = await FirebaseAuth.get_user_by_email(email)
            providers = await FirebaseAuth.get_user_provider_ids(firebase_user["uid"])
            if "password" not in providers:
                raise ConflictException(
                    message=(
                        "An account with this email already exists. "
                        "Please sign in with your social provider."
                    ),
                    error_code=ACCOUNT_EXISTS_USE_LOGIN,
                ) from None
            raise UnauthorizedException(
                message="Incorrect password for an existing account.",
                error_code=INVALID_CREDENTIALS,
            ) from None

        firebase_user = await FirebaseAuth.get_user_by_email(email)
        created_user = await self._create_local_user_from_firebase(
            email=email,
            firebase_uid=firebase_user["uid"],
            email_verified=firebase_user.get("email_verified", False),
            auth_provider="firebase.password",
            display_name=firebase_user.get("display_name"),
        )
        self.logger.info(
            f"[AuthService.register] Resumed registration for Firebase orphan: {email}"
        )
        await self.send_verification_email(email)
        return self._build_registration_response(
            created_user, registration_resumed=True
        )

    async def register_with_firebase(
        self,
        email: EmailStr,
        password: str,
    ) -> dict[str, Any]:
        """Register a new user with Firebase Authentication and return data for login.
        Username will be auto-generated from email.
        Firebase display_name will be auto-generated from email prefix.

        Args:
            email: User email
            password: User password

        Returns:
            Dict: User data and access token

        Raises:
            ConflictException: If user already exists in MongoDB
            UnauthorizedException: If orphan Firebase user password is wrong
            BadRequestException: If Firebase registration fails unexpectedly
        """
        self.logger.info(
            f"[AuthService.register] Attempting to register user. Email: {email}"
        )

        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            self.logger.warning(
                f"Registration failed: Email {email} already registered"
            )
            raise ConflictException(
                message="An account with this email already exists. Please sign in.",
                error_code=EMAIL_ALREADY_REGISTERED,
            )

        firebase_display_name = email.split("@")[0]
        registration_resumed = False

        try:
            self.logger.info(
                f"[AuthService.register] About to call FirebaseAuth.create_user for email: {email}"
            )
            firebase_user_data = await FirebaseAuth.create_user(
                email=email,
                password=password,
                display_name=firebase_display_name,
            )
        except EmailAlreadyExistsError:
            self.logger.info(
                f"[AuthService.register] Firebase user exists without MongoDB record: {email}"
            )
            return await self._sync_orphan_firebase_user(email, password)
        except Exception as e:
            self.logger.error(
                f"Registration process error for email {email}: {str(e)}", exc_info=True
            )
            raise BadRequestException(
                message="Registration failed. Please try again later.",
                error_code=FIREBASE_REGISTRATION_FAILED,
            ) from e

        try:
            created_user = await self._create_local_user_from_firebase(
                email=email,
                firebase_uid=firebase_user_data["uid"],
                email_verified=False,
                auth_provider="firebase.password",
                display_name=firebase_display_name,
            )
            self.logger.info(f"User registered with Firebase: {email}")
            await self.send_verification_email(email)
            return self._build_registration_response(
                created_user, registration_resumed=registration_resumed
            )
        except Exception as e:
            self.logger.error(
                f"Registration process error for email {email}: {str(e)}", exc_info=True
            )
            raise BadRequestException(
                message="Registration failed. Please try again later.",
                error_code=FIREBASE_REGISTRATION_FAILED,
            ) from e

    async def login_with_firebase(self, id_token: str) -> dict[str, Any]:
        """Login with Firebase ID token.

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
                self.logger.warning("Token format does not match expected JWT pattern")
                raise UnauthorizedException("Invalid token format")

            token_data = await FirebaseAuth.verify_token(id_token)
            uid = token_data.get("uid")
            email = token_data.get("email")

            if not uid or not email:
                self.logger.warning(
                    "Firebase token missing required claims (uid or email)"
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
                    provider_data = token_data.get("firebase", {}).get(
                        "sign_in_provider", ""
                    )
                    auth_provider = (
                        f"firebase.{provider_data.split('.')[0]}"
                        if provider_data
                        else "firebase.password"
                    )
                    user = await self._create_local_user_from_firebase(
                        email=email,
                        firebase_uid=uid,
                        email_verified=firebase_user.get("email_verified", False),
                        auth_provider=auth_provider,
                        display_name=firebase_user.get("display_name"),
                    )
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
                user_id = require_object_id(user.id)
                updated_user = await self.user_repository.update(user_id, user)
                if updated_user is not None:
                    user = updated_user

            await self.user_repository.update_last_login(require_object_id(user.id))
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
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Create a JWT access token.

        Args:
            data: Token data
            expires_delta: Token expiration time

        Returns:
            str: JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.auth.jwt_access_token_expire_minutes
            )

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithm=settings.auth.jwt_algorithm,
        )

        return str(encoded_jwt)

    async def send_verification_email(self, email: EmailStr) -> bool:
        """Send a verification email using Firebase.

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
        """Send a password reset email using Firebase and Resend.

        Args:
            email: User email

        Returns:
            bool: True if email sent successfully

        Raises:
            Exception: If email sending fails
        """
        if self.resend_client is None:
            raise RuntimeError(
                "Password reset email is not configured (RESEND__API_KEY missing)"
            )

        try:
            reset_link = await FirebaseAuth.generate_password_reset_link(email)
            subject = "Reset your YARBA password"
            text = (
                "Use the link below to reset your password:\n\n"
                f"{reset_link}\n\n"
                "If you did not request this, you can ignore this email."
            )
            html = (
                "<p>Use the link below to reset your password:</p>"
                f'<p><a href="{reset_link}">Reset password</a></p>'
                "<p>If you did not request this, you can ignore this email.</p>"
            )
            await self.resend_client.send_email(
                to=str(email),
                subject=subject,
                text=text,
                html=html,
            )
            self.logger.info("Password reset email sent to %s", email)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send password reset email: {str(e)}")
            raise

    async def change_firebase_password(
        self, email: EmailStr, current_password: str, new_password: str
    ) -> bool:
        """Change a Firebase user's password.

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
        """Get a user by ID.

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
        """Get a user by email.

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
        self, user_id: PydanticObjectId, update_data: dict[str, Any]
    ) -> User:
        """Update a user.

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

        user.updated_at = datetime.now(UTC)

        try:
            await user.save()
            self.logger.info(f"User updated: {user_id}")
            return user
        except Exception as e:
            self.logger.error(f"Failed to update user: {str(e)}")
            raise NotFoundException("User not found")

    async def update_user_with_firebase(
        self, user_id: PydanticObjectId, update_data: dict[str, Any]
    ) -> User:
        """Update user data in both Firebase and local database.

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
            updated_user = await self.user_repository.update(
                require_object_id(user.id),
                local_update_data,  # type: ignore[arg-type]
            )
            if updated_user is None:
                raise NotFoundException("User not found")
            self.logger.info(f"Successfully updated user {user.email} in local DB.")
            return updated_user

        # Return original user if no local updates were made but Firebase might have been
        return user

    async def update_user_setup_progress(
        self,
        user_id: PydanticObjectId,
        current_setup_step: int | None,
        setup_completed: bool | None,
    ) -> User:
        """Update the user's setup progress.

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

    async def verify_token(self, token: str) -> tuple[dict[str, Any], User]:
        """Verify a JWT token and get the user.

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
        """Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            User: Deactivated user

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(user_id)

        user.is_active = False
        user.updated_at = datetime.now(UTC)

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
