"""Application constants."""

import os
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


class LLMModel(str, Enum):
    """LLM model enum."""

    # OpenAI models
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"

    # Anthropic models
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20240620"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"

    # Gemini models
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"

    # Ollama models
    LLAMA3 = "llama3"
    MISTRAL = "mistral"


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


# Processing mode constants
class ProcessingMode(str, Enum):
    """Processing mode enum."""

    PROCESS = "Process"
    HARDCODE = "Hardcode"
