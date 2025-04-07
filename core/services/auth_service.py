"""Authentication service for user management and authentication."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import EmailStr

from config.logging_config import get_logger
from config.settings import Settings
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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    def __init__(self, user_repository: Optional[UserRepository] = None):
        """
        Initialize the authentication service.

        Args:
            user_repository: Repository for accessing user data
        """
        self.user_repository = user_repository or UserRepository()
        self.logger = get_logger(self.__class__.__name__)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            bool: True if password matches hash, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Get password hash.

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)

    async def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate a user.

        Args:
            email: User email
            password: User password

        Returns:
            User: Authenticated user

        Raises:
            UnauthorizedException: If authentication fails
        """
        # Get user by email
        user = await self.user_repository.get_by_email(email)

        if not user:
            self.logger.warning(
                f"Authentication failed: User with email {email} not found"
            )
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            self.logger.warning(f"Authentication failed: User {user.email} is inactive")
            raise UnauthorizedException("User account is inactive")

        # Make account_locked_until timezone-aware before comparison
        if user.account_locked_until:
            # Convert naive datetime to aware datetime if needed
            locked_until = user.account_locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)

            # Now compare with timezone-aware current time
            current_time = datetime.now(timezone.utc)
            if locked_until > current_time:
                self.logger.warning(
                    f"Authentication failed: User {user.email} account is locked"
                )
                raise UnauthorizedException(
                    f"Account is locked until {locked_until.isoformat()}"
                )

        if not self.verify_password(password, user.hashed_password):
            # Increment login attempts
            login_attempts = await self.user_repository.increment_login_attempts(
                user.email
            )

            # Lock account if too many failed attempts
            if login_attempts >= settings.auth.max_login_attempts:
                lock_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.auth.account_lockout_minutes
                )
                await self.user_repository.lock_account(user.email, lock_until)
                self.logger.warning(
                    f"Account locked: User {user.email} exceeded login attempts"
                )
                raise UnauthorizedException(
                    f"Too many failed login attempts. Account locked until {lock_until.isoformat()}"
                )

            self.logger.warning(
                f"Authentication failed: Invalid password for user {user.email}"
            )
            raise UnauthorizedException("Invalid email or password")

        # Reset login attempts on successful login
        await self.user_repository.reset_login_attempts(user.email)

        # Update last login timestamp
        await self.user_repository.update_last_login(user.id)

        return user

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Perform a login operation.

        Args:
            email: User email
            password: Password

        Returns:
            Dict: Access token and token type

        Raises:
            HTTPException: If login fails
        """
        try:
            logger.info(f"Login attempt for {email}")
            user = await self.authenticate_user(email, password)
            logger.info("Login successful ========================")
            access_token = self.create_access_token(data={"sub": user.email})
            return {"access_token": access_token, "token_type": "bearer"}
        except UnauthorizedException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            self.logger.error(f"Login error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed due to an internal error",
            )

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

    async def register_user(
        self, email: EmailStr, password: str, full_name: str
    ) -> User:
        """
        Register a new user.

        Args:
            email: User email
            password: User password
            full_name: User full name

        Returns:
            User: Created user

        Raises:
            BadRequestException: If user already exists
        """
        # Check if user already exists
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            self.logger.warning(
                f"Registration failed: Email {email} already registered"
            )
            raise BadRequestException("Email already registered")

        # Create new user
        hashed_password = self.get_password_hash(password)

        user = User(
            email=email,
            hashed_password=hashed_password,
            username=full_name,
            is_active=True,
            email_verified=False,
        )

        created_user = await self.user_repository.create(user)
        self.logger.info(f"User registered: {email}")

        return created_user

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
            update_data: User data to update

        Returns:
            User: Updated user

        Raises:
            NotFoundException: If user not found
        """
        user = await self.get_user_by_id(user_id)

        # Update user fields
        for key, value in update_data.items():
            if hasattr(user, key) and key != "id" and key != "hashed_password":
                setattr(user, key, value)

        # Update password if provided
        if "password" in update_data:
            user.hashed_password = self.get_password_hash(update_data["password"])

        # Update timestamp
        user.updated_at = datetime.now(timezone.utc)

        updated_user = await self.user_repository.update(user_id, user)
        if not updated_user:
            self.logger.error(f"Failed to update user: {user_id}")
            raise NotFoundException("User not found")

        self.logger.info(f"User updated: {user_id}")
        return updated_user

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
