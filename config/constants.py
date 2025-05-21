"""Application constants."""

from enum import Enum
from pathlib import Path

# Application paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

# API constants
API_V1_PREFIX = "/api/v1"
API_TAGS_METADATA = [
    {
        "name": "auth",
        "description": "Authentication operations",
    },
    {
        "name": "users",
        "description": "User operations",
    },
    {
        "name": "resumes",
        "description": "Resume operations",
    },
    {
        "name": "cover-letters",
        "description": "Cover letter operations",
    },
    {
        "name": "portfolios",
        "description": "Portfolio operations",
    },
    {
        "name": "health",
        "description": "Health check operations",
    },
]

# Database constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# LaTeX constants
LATEX_EXTENSIONS = [".tex", ".cls", ".sty", ".bib"]
PDF_EXTENSION = ".pdf"
LATEX_COMPILERS = ["pdflatex", "xelatex", "lualatex"]

# Feature flags
FEATURE_FLAGS = {
    "check_clearance": True,
    "linkedin_integration": True,
    "pdf_preview": True,
}

# Application constants
APP_CONSTANTS = {
    "clearance_keywords": [
        "security clearance",
        "clearance required",
        "classified",
        "top secret",
        "secret",
        "confidential",
    ],
}


# LLM constants
class LLMProvider(str, Enum):
    """LLM provider enum."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


# Resume section constants
class ResumeSection(str, Enum):
    """Resume section enum."""

    PERSONAL_INFORMATION = "personal_information"
    CAREER_SUMMARY = "career_summary"
    SKILLS = "skills"
    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    AWARDS = "awards"
    PUBLICATIONS = "publications"
