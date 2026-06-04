"""Application settings and configuration."""

import os
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _should_skip_runtime_directory_creation() -> bool:
    """Skip mkdir during import in CI/pytest where the process cwd may be read-only."""
    return os.environ.get("ENVIRONMENT", "").lower() == "test"


def _ensure_directory(path: Path) -> Path:
    """Create directory when settings load outside test/CI."""
    if not _should_skip_runtime_directory_creation():
        path.mkdir(parents=True, exist_ok=True)
    return path


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="MONGODB_",
        extra="ignore",
    )

    url: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL",
        validation_alias="URI",
    )
    name: str = Field(
        default="rbt", description="Database name", validation_alias="DATABASE"
    )
    min_pool_size: int = Field(
        default=10,
        description="Minimum number of connections in the pool",
    )
    max_pool_size: int = Field(
        default=100,
        description="Maximum number of connections in the pool",
    )
    connection_timeout_ms: int = Field(
        default=30000,
        description="Connection timeout in milliseconds",
    )
    server_selection_timeout_ms: int = Field(
        default=20000,
        description="Server selection timeout in milliseconds",
    )
    socket_timeout_ms: int = Field(
        default=60000,
        description="Socket timeout in milliseconds",
    )
    retry_writes: bool = Field(
        default=True,
        description="Enable retry for write operations",
    )
    retry_reads: bool = Field(
        default=True,
        description="Enable retry for read operations",
    )

    @field_validator("url")
    def validate_url(cls, v: str) -> str:
        """Check if direct MONGODB_URI is set and use it instead."""
        direct_uri = os.environ.get("MONGODB_URI")
        if direct_uri:
            return direct_uri
        return v


class AuthSettings(BaseSettings):
    """Authentication settings."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="",  # No prefix for auth settings to maintain backward compatibility
        extra="ignore",
    )

    # JWT settings for API authentication after Firebase verification
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("your-secret-key"),
        description="Secret key for JWT token generation",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token generation",
        validation_alias="JWT_ALGORITHM",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=1440,  # Set to 24 hours (1440 minutes) for debug purposes
        description="Access token expiration time in minutes",
        validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    # API URLs
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for API endpoints",
        validation_alias="API_BASE_URL",
    )
    email_verification_path: str = Field(
        default="/auth/verify-email",
        description="Path for email verification",
        validation_alias="EMAIL_VERIFICATION_PATH",
    )
    password_reset_path: str = Field(
        default="/auth/reset-password",
        description="Path for password reset",
        validation_alias="PASSWORD_RESET_PATH",
    )

    # Firebase settings
    firebase_api_key: str | None = Field(
        default=None,
        description="Firebase Web API key - required for REST API authentication",
        validation_alias="FIREBASE_API_KEY",
    )
    firebase_type: str = Field(
        default="service_account",
        description="Firebase credential type",
        validation_alias="FIREBASE_TYPE",
    )
    firebase_project_id: str = Field(
        default="",
        description="Firebase project ID",
        validation_alias="FIREBASE_PROJECT_ID",
    )
    firebase_private_key_id: str = Field(
        default="",
        description="Firebase private key ID",
        validation_alias="FIREBASE_PRIVATE_KEY_ID",
    )
    firebase_private_key: str | None = Field(
        default=None,
        description="Firebase private key",
        validation_alias="FIREBASE_PRIVATE_KEY",
    )
    firebase_client_email: str = Field(
        default="",
        description="Firebase client email",
        validation_alias="FIREBASE_CLIENT_EMAIL",
    )
    firebase_client_id: str = Field(
        default="",
        description="Firebase client ID",
        validation_alias="FIREBASE_CLIENT_ID",
    )
    firebase_auth_uri: str = Field(
        default="https://accounts.google.com/o/oauth2/auth",
        description="Firebase auth URI",
        validation_alias="FIREBASE_AUTH_URI",
    )
    firebase_token_uri: str = Field(
        default="https://oauth2.googleapis.com/token",
        description="Firebase token URI",
        validation_alias="FIREBASE_TOKEN_URI",
    )
    firebase_auth_provider_x509_cert_url: str = Field(
        default="https://www.googleapis.com/oauth2/v1/certs",
        description="Firebase auth provider x509 cert URL",
        validation_alias="FIREBASE_AUTH_PROVIDER_X509_CERT_URL",
    )
    firebase_client_x509_cert_url: str = Field(
        default="",
        description="Firebase client x509 cert URL",
        validation_alias="FIREBASE_CLIENT_X509_CERT_URL",
    )
    firebase_universe_domain: str = Field(
        default="googleapis.com",
        description="Firebase universe domain",
        validation_alias="FIREBASE_UNIVERSE_DOMAIN",
    )
    firebase_private_key_base64: str | None = Field(
        default=None,
        description="Firebase private key encoded in base64",
        validation_alias="FIREBASE_PRIVATE_KEY_BASE64",
    )

    @model_validator(mode="after")
    def decode_firebase_base64_key(self) -> Self:
        """Decode base64 private key if present."""
        if not self.firebase_private_key and self.firebase_private_key_base64:
            try:
                import base64
                import logging

                decoded_key = base64.b64decode(self.firebase_private_key_base64).decode(
                    "utf-8"
                )
                self.firebase_private_key = decoded_key
                logging.info("Successfully decoded Firebase private key from base64")
            except Exception as e:
                import logging

                logging.error(f"Failed to decode base64 private key: {str(e)}")

        if self.firebase_private_key and "\\n" in self.firebase_private_key:
            self.firebase_private_key = self.firebase_private_key.replace("\\n", "\n")

        return self

    def get_firebase_credentials_dict(self) -> dict[str, Any]:
        """Get Firebase credentials as a dictionary for firebase-admin.

        Uses credentials directly from environment variables.
        Returns an empty dict if required fields are missing.
        """
        # Check for required fields with more robust empty string check
        if (
            not self.firebase_project_id
            or not self.firebase_private_key
            or not self.firebase_client_email
        ):
            from config.logging_config import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "Missing required Firebase credentials in environment variables"
            )
            logger.warning(f"project_id present: {bool(self.firebase_project_id)}")
            logger.warning(f"private_key present: {bool(self.firebase_private_key)}")
            logger.warning(f"client_email present: {bool(self.firebase_client_email)}")
            return {}

        # Create credentials dictionary with all fields
        credentials_dict = {
            "type": self.firebase_type,
            "project_id": self.firebase_project_id,
            "private_key_id": self.firebase_private_key_id,
            "private_key": self.firebase_private_key,
            "client_email": self.firebase_client_email,
            "client_id": self.firebase_client_id,
            "auth_uri": self.firebase_auth_uri,
            "token_uri": self.firebase_token_uri,
            "auth_provider_x509_cert_url": self.firebase_auth_provider_x509_cert_url,
            "client_x509_cert_url": self.firebase_client_x509_cert_url,
            "universe_domain": self.firebase_universe_domain,
        }

        # Filter out empty values
        return {k: v for k, v in credentials_dict.items() if v}

    @field_validator("api_base_url")
    def validate_api_base_url(cls, v: str) -> str:
        """Validate and normalize API base URL.

        Ensures the URL has a proper scheme and is formatted correctly.

        Args:
            v: API base URL to validate

        Returns:
            str: Validated API base URL

        Raises:
            ValueError: If URL is invalid
        """
        import re

        # Simple validation for URL format
        if not re.match(r"^https?://", v):
            # Auto-prefixing http:// if missing
            v = f"http://{v}"

        # Remove trailing slash if present
        if v.endswith("/"):
            v = v[:-1]

        return v


class LLMSettings(BaseSettings):
    """LLM configuration settings."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key", validation_alias="OPENAI_API_KEY"
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key",
        validation_alias="ANTHROPIC_API_KEY",
    )
    gemini_api_key: str | None = Field(
        default=None,
        description="Google Gemini API key",
        validation_alias="GEMINI_API_KEY",
    )
    default_model: str = Field(
        default="gpt-4.1", description="Default LLM model to use"
    )
    temperature: float = Field(
        default=0.1, description="Default temperature for LLM responses"
    )
    max_tokens: int = Field(default=4000, description="Maximum tokens in LLM responses")
    ollama_uri: str = Field(
        default="http://localhost:11434", description="URI for Ollama API"
    )
    enable_json_schema: bool = Field(
        default=True,
        description="Whether to enable JSON schema output for supported models",
        validation_alias="ENABLE_JSON_SCHEMA",
    )
    json_schema_validation: bool = Field(
        default=True,
        description="Whether to enable client-side JSON schema validation for all models",
        validation_alias="JSON_SCHEMA_VALIDATION",
    )
    json_compatible_models: list[str] = Field(
        default=[
            "gpt-4.1-mini-2025-04-14",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "claude-3-opus",
            "claude-3-sonnet",
            "gemini-1.5-pro",
        ],
        description="List of models known to support JSON schema output",
        validation_alias="JSON_COMPATIBLE_MODELS",
    )

    # Cost tracking settings
    enable_cost_tracking: bool = Field(
        default=True,
        description="Whether to enable cost tracking for LLM calls",
        validation_alias="ENABLE_COST_TRACKING",
    )

    # Use LiteLLM's model cost map
    use_litellm_model_cost_map: bool = Field(
        default=True,
        description="Whether to use LiteLLM's built-in model cost map",
        validation_alias="USE_LITELLM_MODEL_COST_MAP",
    )

    # URL for custom model cost map (optional)
    custom_model_cost_map_url: str | None = Field(
        default=None,
        description="URL to custom model cost map JSON for LiteLLM",
        validation_alias="CUSTOM_MODEL_COST_MAP_URL",
    )

    # Custom price overrides only for models not in LiteLLM's cost map
    # These are provided as fallbacks and can be empty if using LiteLLM's cost map
    model_pricing: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Custom price overrides for LLM models not in LiteLLM's model cost map",
    )


class LinkedInSettings(BaseSettings):
    """LinkedIn settings for job scraping.

    Note: These settings are user-specific and should not be used globally.
    Credentials should be stored in the user's profile in the database.
    These settings are provided as fallbacks or for testing purposes only.
    """

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="LINKEDIN_",
    )

    email: str | None = Field(
        default=None,
        description="LinkedIn email for authentication (user-specific)",
        validation_alias="EMAIL",
    )
    password: str | None = Field(
        default=None,
        description="LinkedIn password for authentication (user-specific)",
        validation_alias="PASSWORD",
    )


class LatexSettings(BaseSettings):
    """LaTeX configuration settings."""

    compiler_path: str = Field(default="pdflatex", description="Path to LaTeX compiler")
    output_dir: Path = Field(
        default=Path("output"), description="Directory for LaTeX output files"
    )
    templates_dir: Path = Field(
        default=Path("templates/latex"), description="Directory for LaTeX templates"
    )
    temp_extensions: list[str] = Field(
        default=[".aux", ".log", ".out"],
        description="Extensions of temporary files to clean up",
    )
    compiler_options: list[str] = Field(
        default_factory=lambda: ["-interaction=nonstopmode"],
        description="Command line options for the compiler",
    )
    cleanup_temp_files: bool = Field(
        default=True, description="Whether to clean up temporary files"
    )
    suppress_logs: bool = Field(
        default=True, description="Whether to suppress LaTeX logs in terminal output"
    )
    log_level: str = Field(
        default="ERROR",
        description="Log level for LaTeX compilation ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')",
    )

    # Default templates
    default_resume_template_id: str = Field(
        default="classic", description="Default resume template ID"
    )
    default_cover_letter_template_id: str = Field(
        default="standard", description="Default cover letter template ID"
    )

    @field_validator("output_dir", "templates_dir")
    def create_directory_if_not_exists(cls, v: Path) -> Path:
        """Create directory if it doesn't exist."""
        return _ensure_directory(v)

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


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
    log_file: Path | None = Field(
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

    @field_validator("log_level")
    def uppercase_log_level(cls, v: str) -> str:
        """Convert log level to uppercase to handle case-insensitive input."""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("log_file")
    def create_log_directory_if_not_exists(cls, v: Path | None) -> Path | None:
        """Create log directory if it doesn't exist."""
        if v:
            v.parent.mkdir(parents=True, exist_ok=True)
        return v


class PreferenceSettings(BaseSettings):
    """Default preference settings for user profiles.

    These settings serve as fallbacks when user-specific preferences are not available
    or when specific fields are missing.
    """

    # Default LaTeX template preferences
    default_latex_templates: dict[str, str] = Field(
        default={
            "default_resume_template_id": "classic",
            "default_cover_letter_template_id": "standard",
        },
        description="Default LaTeX template IDs",
    )

    # Career summary preferences
    career_summary_min_words: int = Field(
        default=15,
        description="Minimum words in career summary",
        validation_alias="PREF_CAREER_SUMMARY_MIN_WORDS",
    )
    career_summary_max_words: int = Field(
        default=25,
        description="Maximum words in career summary",
        validation_alias="PREF_CAREER_SUMMARY_MAX_WORDS",
    )

    # Work experience preferences
    work_experience_max_jobs: int = Field(
        default=4,
        description="Maximum number of jobs to include",
        validation_alias="PREF_WORK_EXPERIENCE_MAX_JOBS",
    )
    work_experience_bullet_points_per_job: int = Field(
        default=3,
        description="Number of bullet points per job",
        validation_alias="PREF_WORK_EXPERIENCE_BULLET_POINTS",
    )

    # Project preferences
    project_max_projects: int = Field(
        default=4,
        description="Maximum number of projects to include",
        validation_alias="PREF_PROJECT_MAX_PROJECTS",
    )
    project_bullet_points_per_project: int = Field(
        default=3,
        description="Number of bullet points per project",
        validation_alias="PREF_PROJECT_BULLET_POINTS",
    )

    # Cover letter preferences
    cover_letter_paragraphs: int = Field(
        default=5,
        description="Number of paragraphs in cover letter",
        validation_alias="PREF_COVER_LETTER_PARAGRAPHS",
    )
    cover_letter_target_age: int = Field(
        default=25,
        description="Target age level for cover letter readability",
        validation_alias="PREF_COVER_LETTER_AGE_LEVEL",
    )

    # Skills preferences
    skills_max_categories: int = Field(
        default=5,
        description="Maximum number of skill categories",
        validation_alias="PREF_SKILLS_MAX_CATEGORIES",
    )
    skills_min_per_category: int = Field(
        default=8,
        description="Minimum skills per category",
        validation_alias="PREF_SKILLS_MIN_PER_CATEGORY",
    )
    skills_max_per_category: int = Field(
        default=10,
        description="Maximum skills per category",
        validation_alias="PREF_SKILLS_MAX_PER_CATEGORY",
    )

    # Education preferences
    education_max_entries: int = Field(
        default=3,
        description="Maximum number of education entries",
        validation_alias="PREF_EDUCATION_MAX_ENTRIES",
    )
    education_max_courses: int = Field(
        default=6,
        description="Maximum number of courses per education entry",
        validation_alias="PREF_EDUCATION_MAX_COURSES",
    )

    # Awards preferences
    awards_max_awards: int = Field(
        default=4,
        description="Maximum number of awards to include",
        validation_alias="PREF_AWARDS_MAX_AWARDS",
    )

    # Publications preferences
    publications_max_publications: int = Field(
        default=3,
        description="Maximum number of publications to include",
        validation_alias="PREF_PUBLICATIONS_MAX_PUBLICATIONS",
    )

    def get_prompt_variables(self) -> dict[str, Any]:
        """Get formatted dictionary of preferences for prompt variables.

        Returns:
            Dict[str, Any]: Dictionary of preference values in the format needed for prompt templates
        """
        # Create a nested structure that directly matches the profile.prompt_preferences structure
        # This aligns with how the prompt templates reference variables
        return {
            "career_summary": {
                "min_words": self.career_summary_min_words,
                "max_words": self.career_summary_max_words,
            },
            "skills": {
                "max_categories": self.skills_max_categories,
                "min_per_category": self.skills_min_per_category,
                "max_per_category": self.skills_max_per_category,
            },
            "work_experience": {
                "max_jobs": self.work_experience_max_jobs,
                "bullet_points_per_job": self.work_experience_bullet_points_per_job,
            },
            "education": {
                "max_entries": self.education_max_entries,
                "max_courses": self.education_max_courses,
            },
            "project": {
                "max_projects": self.project_max_projects,
                "bullet_points_per_project": self.project_bullet_points_per_project,
            },
            "publications": {
                "max_publications": self.publications_max_publications,
            },
            "awards": {
                "max_awards": self.awards_max_awards,
            },
            "cover_letter": {
                "paragraphs": self.cover_letter_paragraphs,
                "target_age": self.cover_letter_target_age,
            },
        }


class APISettings(BaseSettings):
    """API settings."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="API_",
    )

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "https://www.yarba.app"],
        description="List of allowed CORS origins",
        validation_alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Whether to allow credentials",
    )
    cors_allow_methods: list[str] = Field(
        default=["*"],
        description="List of allowed HTTP methods",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        description="List of allowed HTTP headers",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from a string or list."""
        import json

        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

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
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for API endpoints",
        validation_alias="BASE_URL",
    )

    # Rate limiting settings
    rate_limit: int = Field(
        default=60,
        description="Default requests per minute limit",
    )
    rate_limit_window: int = Field(
        default=60,
        description="Default time window in seconds for rate limiting",
    )
    pdf_rate_limit: int = Field(
        default=3,
        description="Requests per minute limit for PDF generation",
    )
    pdf_rate_limit_window: int = Field(
        default=120,
        description="Time window in seconds for PDF generation rate limiting",
    )


class ResendSettings(BaseSettings):
    """Resend email settings for inbound webhooks and outbound delivery."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="RESEND__",
    )

    api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Resend API key (re_...)",
        validation_alias="API_KEY",
    )
    webhook_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Resend webhook signing secret (whsec_...)",
        validation_alias="WEBHOOK_SECRET",
    )
    from_address: str = Field(
        default="resumes@yarba.app",
        description="Sender address for outbound resume emails",
        validation_alias="FROM",
    )


class EmailSettings(BaseSettings):
    """Email integration settings."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="EMAIL__",
    )

    provider: Literal["resend"] = Field(
        default="resend",
        description="Outbound/inbound email provider",
    )


class FeatureSettings(BaseSettings):
    """Settings for application features and toggles."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="FEATURE_",
    )

    enable_email_to_resume: bool = Field(
        default=False,
        description="Enable email-to-resume via Resend inbound webhook",
        validation_alias="ENABLE_EMAIL_TO_RESUME",
    )

    enable_clearance_check: bool = Field(
        default=True,
        description="Enable check for clearance requirements in job descriptions.",
        validation_alias="ENABLE_CLEARANCE_CHECK",
    )

    # Optimized restriction keywords (consolidated clearance and citizenship requirements)
    restriction_keywords: list[str] = Field(
        default=[
            # Security clearance keywords (specific phrases to avoid false positives)
            "security clearance",
            "clearance required",
            "active clearance",
            "maintain clearance",
            "obtain clearance",
            "clearance eligible",
            "top secret clearance",
            "secret clearance",
            "confidential clearance",
            "public trust clearance",
            "ts/sci clearance",
            "polygraph required",
            "background investigation",
            "q clearance",
            "l clearance",
            "nato secret",
            "cosmic top secret",
            # US citizenship requirements
            "us citizen required",
            "u.s. citizen required",
            "us citizenship required",
            "u.s. citizenship required",
            "must be us citizen",
            "must be u.s. citizen",
            "citizen of the united states",
            "american citizen required",
            "born in the usa",
            "naturalized citizen",
        ],
        description="Keywords indicating security clearance or citizenship requirements.",
        validation_alias="RESTRICTION_KEYWORDS",
    )

    @field_validator("restriction_keywords", mode="before")
    @classmethod
    def parse_keyword_lists(cls, v):
        """Parse keyword lists from a string or list."""
        import json

        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [kw.strip() for kw in v.split(",")]
        return v


class StorageSettings(BaseSettings):
    """Storage settings for file uploads and media."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="STORAGE_",
    )

    # Storage provider
    provider: str = Field(
        default="aws_s3", description="Storage provider (local, s3, etc.)"
    )

    # AWS S3 settings
    aws_access_key: str | None = Field(
        default=None,
        description="AWS S3 access key",
        validation_alias="AWS_ACCESS_KEY",
    )
    aws_secret_key: str | None = Field(
        default=None,
        description="AWS S3 secret key",
        validation_alias="AWS_SECRET_KEY",
    )
    aws_region: str | None = Field(
        default="us-east-1",  # Restoring default as per your previous working version
        description="AWS S3 region",
        validation_alias="AWS_REGION",  # Ensuring explicit mapping
    )
    aws_bucket: str = Field(
        default="yarba-local",
        description="AWS S3 bucket name for storing all content",
        validation_alias="AWS_BUCKET",
    )
    aws_use_presigned_urls: bool = Field(
        default=False,
        description="Whether to use pre-signed URLs for AWS S3",
        validation_alias="AWS_USE_PRESIGNED_URLS",
    )
    aws_presigned_url_expiry: int = Field(
        default=3600,  # 1 hour
        description="Expiry time in seconds for pre-signed URLs",
        validation_alias="AWS_PRESIGNED_URL_EXPIRY",
    )

    # CloudFront settings
    cloudfront_enabled: bool = Field(
        default=False,  # This might be re-evaluated based on the new architecture. Keeping for now.
        description="Whether to use CloudFront for distribution",
        validation_alias="CLOUDFRONT_ENABLED",
    )
    cloudfront_distribution_id: str | None = Field(  # New field
        default=None,
        description="The ID of the single, shared CloudFront distribution for portfolios",
        validation_alias="CLOUDFRONT_DISTRIBUTION_ID",
    )
    cloudfront_domain: str | None = Field(
        default=None,
        description="CloudFront distribution domain (can be derived or set if needed for other purposes)",
        validation_alias="CLOUDFRONT_DOMAIN",
    )
    cloudfront_key_pair_id: str | None = Field(
        default=None,
        description="CloudFront key pair ID for signed URLs",
        validation_alias="CLOUDFRONT_KEY_PAIR_ID",
    )
    cloudfront_private_key_path: Path | None = Field(
        default=None,
        description="Path to CloudFront private key for signed URLs",
        validation_alias="CLOUDFRONT_PRIVATE_KEY_PATH",
    )
    cloudfront_url_expiry: int = Field(
        default=86400,  # 24 hours
        description="Expiry time in seconds for CloudFront signed URLs",
        validation_alias="CLOUDFRONT_URL_EXPIRY",
    )

    # Local storage settings
    local_storage_path: str = Field(
        default="uploads", description="Path for local storage"
    )

    # Media paths
    profile_pictures_path: str = Field(
        default="profile_pictures",
        description="Subdirectory for profile pictures within local storage",
    )
    signatures_path: str = Field(
        default="signatures",
        description="Path for signature storage",
        validation_alias="SIGNATURES_PATH",
    )
    resumes_path: str = Field(
        default="resumes",
        description="Path for resume PDFs storage",
        validation_alias="RESUMES_PATH",
    )
    cover_letters_path: str = Field(
        default="cover-letters",
        description="Path for cover letter PDFs storage",
        validation_alias="COVER_LETTERS_PATH",
    )

    # Media settings
    max_image_size: int = Field(
        default=5 * 1024 * 1024,
        description="Maximum image size in bytes (5MB)",
        validation_alias="MAX_IMAGE_SIZE",
    )
    max_pdf_size: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum PDF size in bytes (10MB)",
        validation_alias="MAX_PDF_SIZE",
    )
    allowed_image_types: list[str] = Field(
        default=["image/jpeg", "image/png", "image/gif", "image/webp"],
        description="Allowed image MIME types",
        validation_alias="ALLOWED_IMAGE_TYPES",
    )

    # New field
    aws_acm_certificate_arn: str | None = Field(
        default=None, description="AWS ACM certificate ARN for CloudFront"
    )

    @field_validator("local_storage_path")
    def create_directory_if_not_exists(cls, v: str) -> Path:
        """Create directory if it doesn't exist."""
        return _ensure_directory(Path(v))


class SeleniumSettings(BaseSettings):
    """Selenium / Chrome WebDriver settings."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="SELENIUM_",
        extra="ignore",
    )

    headless: bool = Field(default=True, description="Run Chrome in headless mode")
    chromedriver_path: str | None = Field(
        default=None, description="Path to chromedriver executable"
    )
    disable_gpu: bool = Field(default=True, description="Disable GPU in Chrome")
    window_size: str = Field(default="1920,1080", description="Chrome window size")
    disable_extensions: bool = Field(
        default=True, description="Disable Chrome extensions"
    )
    no_sandbox: bool = Field(default=True, description="Run Chrome with --no-sandbox")
    disable_dev_shm_usage: bool = Field(
        default=True, description="Disable /dev/shm usage in Chrome"
    )
    connection_timeout: int = Field(default=30, description="Script timeout in seconds")
    page_load_timeout: int = Field(
        default=60, description="Page load timeout in seconds"
    )
    implicit_wait: int = Field(default=10, description="Implicit wait in seconds")
    max_retries: int = Field(default=3, description="Max WebDriver init retries")
    retry_delay: int = Field(default=2, description="Delay between retries in seconds")
    kill_existing_processes: bool = Field(
        default=True, description="Kill existing Chrome processes before start"
    )
    container_chrome_path: str = Field(
        default="/usr/bin/google-chrome",
        description="Chrome binary path in containerized environments",
    )
    chrome_profiles_base_dir: Path = Field(
        default=Path("chrome_profiles"),
        description="Base directory for per-user Chrome profiles",
    )

    def get_user_chrome_profile_dir(self, user_id: str) -> Path:
        """Return the Chrome profile directory for a user."""
        profile_dir = self.chrome_profiles_base_dir / user_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir

    def is_containerized(self) -> bool:
        """Detect if the app is running in a container."""
        return Path("/.dockerenv").exists() or os.environ.get(
            "CONTAINER", ""
        ).lower() in {"1", "true", "yes"}


class PathSettings(BaseSettings):
    """Path settings."""

    base_dir: Path = Field(
        default=Path().absolute(),
        description="Base directory of the application",
    )

    temp_dir: Path = Field(
        default=Path("temp"),
        description="Directory for temporary files",
    )

    prompts_dir: Path = Field(
        default=Path("prompts"),
        description="Directory for prompt templates (relative to project root)",
    )

    output_dir: Path = Field(
        default=Path("output"),
        description="Directory for output files",
    )

    @field_validator("temp_dir", "prompts_dir", "output_dir")
    def create_directory_if_not_exists(cls, v: Path) -> Path:
        """Create directory if it doesn't exist."""
        return _ensure_directory(v)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
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
    test_user_id: Any = Field(
        default="000000000000000000000000",
        description="Test user ID",
        validation_alias="TEST_USER_ID",
    )

    @field_validator("test_user_id")
    def validate_test_user_id(cls, v: str) -> Any:
        """Convert string test_user_id to PydanticObjectId if valid."""
        try:
            from beanie.odm.fields import PydanticObjectId
            from bson import ObjectId

            if isinstance(v, str) and ObjectId.is_valid(v):
                return PydanticObjectId(v)
            else:
                from config.logging_config import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    f"Invalid test_user_id format: {v}. Using default placeholder."
                )
                return PydanticObjectId("000000000000000000000000")
        except ImportError:
            # Handle case where bson or beanie is not available (e.g., during initial setup)
            return v

    # Components
    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings, description="Database settings"
    )
    auth: AuthSettings = Field(
        default_factory=AuthSettings, description="Auth settings"
    )
    llm: LLMSettings = Field(default_factory=LLMSettings, description="LLM settings")
    linkedin: LinkedInSettings = Field(
        default_factory=LinkedInSettings,
        description="LinkedIn settings (user-specific)",
    )
    latex: LatexSettings = Field(
        default_factory=LatexSettings, description="LaTeX settings"
    )
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging settings"
    )
    preferences: PreferenceSettings = Field(
        default_factory=PreferenceSettings,
        description="Default user preference settings",
    )
    api: APISettings = Field(default_factory=APISettings, description="API settings")
    paths: PathSettings = Field(
        default_factory=PathSettings, description="Path settings"
    )
    storage: StorageSettings = Field(
        default_factory=StorageSettings, description="Storage settings"
    )
    features: FeatureSettings = Field(
        default_factory=FeatureSettings, description="Feature toggle settings"
    )
    email: EmailSettings = Field(
        default_factory=EmailSettings, description="Email integration settings"
    )
    resend: ResendSettings = Field(
        default_factory=ResendSettings, description="Resend email settings"
    )
    selenium: SeleniumSettings = Field(
        default_factory=SeleniumSettings, description="Selenium settings"
    )

    # Convenience properties
    @property
    def chrome_profiles_dir(self) -> Path:
        """Get base directory for Chrome profiles."""
        return self.selenium.chrome_profiles_base_dir

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
    def cors_origins(self) -> list[str]:
        """Get CORS origins."""
        return self.api.cors_origins

    @property
    def linkedin_email(self) -> str | None:
        """Get LinkedIn email."""
        return self.linkedin.email

    @property
    def linkedin_password(self) -> str | None:
        """Get LinkedIn password."""
        return self.linkedin.password


# Create settings instance
settings = Settings()


def get_settings() -> Settings:
    """Return the global settings instance."""
    return settings
