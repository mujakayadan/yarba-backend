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
    ollama_uri: str = Field(
        default="http://localhost:11434", description="URI for Ollama API"
    )


class LinkedInSettings(BaseSettings):
    """LinkedIn settings for job scraping."""

    email: Optional[str] = Field(
        default=None, description="LinkedIn email for authentication"
    )
    password: Optional[str] = Field(
        default=None, description="LinkedIn password for authentication"
    )


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
    templates_dir: Path = Field(
        default=Path("templates/latex"), description="Directory for LaTeX templates"
    )
    temp_extensions: List[str] = Field(
        default=[".aux", ".log", ".out"],
        description="Extensions of temporary files to clean up",
    )
    compiler_options: List[str] = Field(
        default_factory=lambda: ["-interaction=nonstopmode"],
        description="Command line options for the compiler",
    )
    cleanup_temp_files: bool = Field(
        default=True, description="Whether to clean up temporary files"
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


class PreferenceSettings(BaseSettings):
    """Default preference settings for user profiles.

    These settings serve as fallbacks when user-specific preferences are not available
    or when specific fields are missing.
    """

    # Career summary preferences
    career_summary_min_words: int = Field(
        default=15,
        description="Minimum words in career summary",
        env="PREF_CAREER_SUMMARY_MIN_WORDS",
    )
    career_summary_max_words: int = Field(
        default=25,
        description="Maximum words in career summary",
        env="PREF_CAREER_SUMMARY_MAX_WORDS",
    )

    # Work experience preferences
    work_experience_max_jobs: int = Field(
        default=4,
        description="Maximum number of jobs to include",
        env="PREF_WORK_EXPERIENCE_MAX_JOBS",
    )
    work_experience_bullet_points_per_job: int = Field(
        default=3,
        description="Number of bullet points per job",
        env="PREF_WORK_EXPERIENCE_BULLET_POINTS",
    )

    # Project preferences
    project_max_projects: int = Field(
        default=4,
        description="Maximum number of projects to include",
        env="PREF_PROJECT_MAX_PROJECTS",
    )
    project_bullet_points_per_project: int = Field(
        default=3,
        description="Number of bullet points per project",
        env="PREF_PROJECT_BULLET_POINTS",
    )

    # Cover letter preferences
    cover_letter_paragraphs: int = Field(
        default=4,
        description="Number of paragraphs in cover letter",
        env="PREF_COVER_LETTER_PARAGRAPHS",
    )
    cover_letter_target_grade_level: int = Field(
        default=12,
        description="Target grade level for cover letter readability",
        env="PREF_COVER_LETTER_GRADE_LEVEL",
    )

    # Skills preferences
    skills_max_categories: int = Field(
        default=5,
        description="Maximum number of skill categories",
        env="PREF_SKILLS_MAX_CATEGORIES",
    )
    skills_min_per_category: int = Field(
        default=3,
        description="Minimum skills per category",
        env="PREF_SKILLS_MIN_PER_CATEGORY",
    )
    skills_max_per_category: int = Field(
        default=10,
        description="Maximum skills per category",
        env="PREF_SKILLS_MAX_PER_CATEGORY",
    )

    # Education preferences
    education_max_entries: int = Field(
        default=3,
        description="Maximum number of education entries",
        env="PREF_EDUCATION_MAX_ENTRIES",
    )
    education_max_courses: int = Field(
        default=4,
        description="Maximum number of courses per education entry",
        env="PREF_EDUCATION_MAX_COURSES",
    )

    # Awards preferences
    awards_max_awards: int = Field(
        default=4,
        description="Maximum number of awards to include",
        env="PREF_AWARDS_MAX_AWARDS",
    )

    # Publications preferences
    publications_max_publications: int = Field(
        default=3,
        description="Maximum number of publications to include",
        env="PREF_PUBLICATIONS_MAX_PUBLICATIONS",
    )

    # Get variable mapping for prompt templates
    def get_prompt_variables(self) -> Dict[str, Any]:
        """Get flattened dictionary of preferences for prompt variables.

        Returns:
            Dict[str, Any]: Dictionary of preference values in the format needed for prompt templates
        """
        values = self.model_dump()
        result = {}

        # Map from settings format to prompt variable format
        mappings = {
            "career_summary_min_words": "career_summary_details_min_words",
            "career_summary_max_words": "career_summary_details_max_words",
            "work_experience_max_jobs": "work_experience_details_max_jobs",
            "work_experience_bullet_points_per_job": "work_experience_details_bullet_points_per_job",
            "project_max_projects": "project_details_max_projects",
            "project_bullet_points_per_project": "project_details_bullet_points_per_project",
            "cover_letter_paragraphs": "cover_letter_details_paragraphs",
            "cover_letter_target_grade_level": "cover_letter_details_target_grade_level",
            "skills_max_categories": "skills_details_max_categories",
            "skills_min_per_category": "skills_details_min_skills_per_category",
            "skills_max_per_category": "skills_details_max_skills_per_category",
            "education_max_entries": "education_details_max_entries",
            "education_max_courses": "education_details_max_courses",
            "awards_max_awards": "awards_details_max_awards",
            "publications_max_publications": "publications_details_max_publications",
        }

        for key, prompt_key in mappings.items():
            if key in values:
                result[prompt_key] = values[key]

        return result


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
        default=Path("/prompts"),
        description="Directory for prompt templates",
    )

    output_dir: Path = Field(
        default=Path("output"),
        description="Directory for output files",
    )

    @field_validator("temp_dir", "prompts_dir", "output_dir")
    def create_directory_if_not_exists(cls, v: Path) -> Path:
        """Create directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v


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
    test_user_id: Any = Field(
        default="000000000000000000000000",
        description="Test user ID",
        env="TEST_USER_ID",
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
        default_factory=LinkedInSettings, description="LinkedIn settings"
    )
    ui: UISettings = Field(default_factory=UISettings, description="UI settings")
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

    @property
    def linkedin_email(self) -> Optional[str]:
        """Get LinkedIn email."""
        return self.linkedin.email

    @property
    def linkedin_password(self) -> Optional[str]:
        """Get LinkedIn password."""
        return self.linkedin.password


# Create settings instance
settings = Settings()
