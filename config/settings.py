"""Application settings and configuration."""

import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    url: str = Field(
        default="mongodb://localhost:27017", description="MongoDB connection URL"
    )
    name: str = Field(default="rbt", description="Database name")
    min_pool_size: int = Field(
        default=10, description="Minimum number of connections in the pool"
    )
    max_pool_size: int = Field(
        default=100, description="Maximum number of connections in the pool"
    )


class AuthSettings(BaseSettings):
    """Authentication settings."""

    # JWT settings
    jwt_secret_key: SecretStr = Field(
        default="your-secret-key",
        description="Secret key for JWT token generation",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token generation",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    password_reset_token_expire_hours: int = Field(
        default=24,
        description="Password reset token expiration time in hours",
    )
    verification_token_expire_hours: int = Field(
        default=48,
        description="Email verification token expiration time in hours",
    )
    max_login_attempts: int = Field(
        default=5,
        description="Maximum number of login attempts before account lockout",
    )
    account_lockout_minutes: int = Field(
        default=15,
        description="Account lockout time in minutes after max login attempts",
    )


class LLMSettings(BaseSettings):
    """LLM configuration settings."""

    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(
        default=None, description="Anthropic API key"
    )
    gemini_api_key: Optional[str] = Field(
        default=None, description="Google Gemini API key"
    )
    default_model: str = Field(
        default="claude-3-sonnet-20240229", description="Default LLM model to use"
    )
    temperature: float = Field(
        default=0.7, description="Default temperature for LLM responses"
    )
    max_tokens: int = Field(default=2000, description="Maximum tokens in LLM responses")


class UISettings(BaseSettings):
    """UI configuration settings."""

    title: str = Field(default="Resume Builder", description="Application title")
    description: str = Field(
        default="Build professional resumes and cover letters",
        description="Application description",
    )
    page_icon: str = Field(default="📄", description="Application page icon")
    layout_type: str = Field(
        default="wide", description="Layout type (wide or centered)"
    )
    initial_sidebar_state: str = Field(
        default="expanded", description="Initial state of the sidebar"
    )
    theme: Dict[str, Any] = Field(
        default={
            "primary_color": "#0066cc",
            "secondary_color": "#f0f2f6",
            "text_color": "#262730",
            "background_color": "#ffffff",
        },
        description="UI theme colors",
    )
    layout: Dict[str, Any] = Field(
        default={"max_width": "1200px", "padding": "2rem"},
        description="UI layout settings",
    )


class LatexSettings(BaseSettings):
    """LaTeX configuration settings."""

    compiler_path: str = Field(default="pdflatex", description="Path to LaTeX compiler")
    output_dir: Path = Field(
        default=Path("output"), description="Directory for LaTeX output files"
    )
    cleanup_temp_files: bool = Field(
        default=True, description="Whether to clean up temporary files"
    )
    temp_extensions: List[str] = Field(
        default=[".aux", ".log", ".out"],
        description="Extensions of temporary files to clean up",
    )


class LoggingSettings(BaseSettings):
    """Logging settings."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )
    log_file: Optional[Path] = Field(
        default=Path("./logs/app.log"),
        description="Log file path",
    )
    log_to_console: bool = Field(
        default=True,
        description="Whether to log to console",
    )
    log_to_file: bool = Field(
        default=True,
        description="Whether to log to file",
    )
    log_file_max_size: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum log file size in bytes",
    )
    log_file_backup_count: int = Field(
        default=5,
        description="Number of log file backups to keep",
    )

    @field_validator("log_file")
    def create_log_directory_if_not_exists(cls, v: Optional[Path]) -> Optional[Path]:
        """Create log directory if it doesn't exist."""
        if v:
            v.parent.mkdir(parents=True, exist_ok=True)
        return v


class APISettings(BaseSettings):
    """API settings."""

    # CORS settings
    cors_origins: List[Union[str, AnyHttpUrl]] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        description="List of allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Whether to allow credentials",
    )
    cors_allow_methods: List[str] = Field(
        default=["*"],
        description="List of allowed HTTP methods",
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="List of allowed HTTP headers",
    )

    # API settings
    api_prefix: str = Field(
        default="/api/v1",
        description="API prefix",
    )
    debug: bool = Field(
        default=False,
        description="Whether to enable debug mode",
    )
    docs_url: str = Field(
        default="/docs",
        description="URL for API documentation",
    )
    redoc_url: str = Field(
        default="/redoc",
        description="URL for ReDoc documentation",
    )
    openapi_url: str = Field(
        default="/openapi.json",
        description="URL for OpenAPI schema",
    )
    title: str = Field(
        default="Resume Builder API",
        description="API title",
    )
    description: str = Field(
        default="API for building resumes and cover letters",
        description="API description",
    )
    version: str = Field(
        default="1.0.0",
        description="API version",
    )


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",
    )

    # Environment
    env: str = Field(
        default="development",
        description="Environment (development, staging, production)",
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Application
    app_name: str = Field(default="Resume Builder", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")

    # Testing
    test_user_id: str = Field(default="test_user", description="Test user ID")

    # Components
    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings, description="Database settings"
    )
    auth: AuthSettings = Field(default_factory=AuthSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings, description="LLM settings")
    ui: UISettings = Field(default_factory=UISettings, description="UI settings")
    latex: LatexSettings = Field(
        default_factory=LatexSettings, description="LaTeX settings"
    )
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    api: APISettings = Field(default_factory=APISettings)

    # Convenience properties
    @property
    def mongodb_uri(self) -> str:
        """Get MongoDB URI."""
        return self.database.url

    @property
    def mongodb_database(self) -> str:
        """Get MongoDB database name."""
        return self.database.name

    @property
    def jwt_secret_key(self) -> SecretStr:
        """Get JWT secret key."""
        return self.auth.jwt_secret_key

    @property
    def jwt_algorithm(self) -> str:
        """Get JWT algorithm."""
        return self.auth.jwt_algorithm

    @property
    def jwt_access_token_expire_minutes(self) -> int:
        """Get JWT access token expiration time."""
        return self.auth.jwt_access_token_expire_minutes

    @property
    def cors_origins(self) -> List[Union[str, AnyHttpUrl]]:
        """Get CORS origins."""
        return self.api.cors_origins


# Create settings instance
settings = Settings()
