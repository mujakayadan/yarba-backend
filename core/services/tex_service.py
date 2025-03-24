"""Tex service for handling TeX templates, headers, and preambles."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from beanie import PydanticObjectId

from core.repositories.preamble_repository import (
    PreambleRepository,
    get_preamble_repository,
)
from core.repositories.tex_header_repository import (
    TexHeaderRepository,
    get_tex_header_repository,
)
from core.repositories.tex_template_repository import (
    TexTemplateRepository,
    get_tex_template_repository,
)

from ..models.cover_letter import CoverLetter
from ..models.portfolio import Portfolio
from ..models.profile import Profile
from ..models.resume import Resume


class TexService:
    """Service for handling TeX templates, headers, and preambles."""

    def __init__(
        self,
        header_repository: Optional[TexHeaderRepository] = None,
        template_repository: Optional[TexTemplateRepository] = None,
        preamble_repository: Optional[PreambleRepository] = None,
    ):
        """
        Initialize the Tex service.

        Args:
            header_repository: Repository for TeX headers
            template_repository: Repository for TeX templates
            preamble_repository: Repository for LaTeX preambles
        """
        self.header_repository = header_repository or get_tex_header_repository()
        self.template_repository = template_repository or get_tex_template_repository()
        self.preamble_repository = preamble_repository or get_preamble_repository()
        self.logger = logging.getLogger(__name__)

    # Template methods
    async def get_template(self, template_name: str) -> Optional[str]:
        """
        Get a template by name.

        Args:
            template_name: Name of the template

        Returns:
            Template content if found, None otherwise
        """
        template = await self.template_repository.get_by_name(template_name)
        if template:
            return template.content
        self.logger.warning(f"Template '{template_name}' not found")
        return None

    async def format_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Format a template with the given parameters.

        Args:
            template_name: Name of the template
            **kwargs: Parameters to format the template with

        Returns:
            Formatted template if successful, None otherwise
        """
        try:
            template = await self.template_repository.get_by_name(template_name)
            if not template:
                self.logger.warning(f"Template '{template_name}' not found")
                return None

            return self.template_repository.safe_format_template(template, **kwargs)
        except ValueError as e:
            self.logger.error(f"Error formatting template '{template_name}': {e}")
            return None

    # Header methods
    async def get_header(self, header_name: str) -> Optional[str]:
        """
        Get a header by name.

        Args:
            header_name: Name of the header

        Returns:
            Header content if found, None otherwise
        """
        header = await self.header_repository.get_by_name(header_name)
        if header:
            return header.content
        self.logger.warning(f"Header '{header_name}' not found")
        return None

    async def format_header(self, header_name: str, **kwargs) -> Optional[str]:
        """
        Format a header with the given parameters.

        Args:
            header_name: Name of the header
            **kwargs: Parameters to format the header with

        Returns:
            Formatted header if successful, None otherwise
        """
        try:
            header = await self.header_repository.get_by_name(header_name)
            if not header:
                self.logger.warning(f"Header '{header_name}' not found")
                return None

            return header.content.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"KeyError in header '{header_name}': {e}")
            return None
        except ValueError as e:
            self.logger.error(f"ValueError in header '{header_name}': {e}")
            return None

    async def get_all_headers_by_category(self, category: str) -> List[Dict[str, str]]:
        """
        Get all headers for a specific category.

        Args:
            category: Category of headers to get

        Returns:
            List of dictionaries with name and content
        """
        headers = await self.header_repository.get_all_by_category(category)
        return [{"name": h.name, "content": h.content} for h in headers]

    async def get_all_header_names_by_category(self, category: str) -> List[str]:
        """
        Get all header names for a specific category.

        Args:
            category: Category of headers to get

        Returns:
            List of header names
        """
        headers = await self.header_repository.get_all_by_category(category)
        return [header.name for header in headers]

    # Preamble methods
    async def get_default_preamble(
        self, preamble_type: str = "resume_preamble"
    ) -> Optional[str]:
        """
        Get the default preamble for a specific type.

        Args:
            preamble_type: Type of preamble (default: resume_preamble)

        Returns:
            Default preamble content if found, None otherwise
        """
        preamble = await self.preamble_repository.get_default(preamble_type)
        if preamble:
            return preamble.content
        self.logger.warning(f"Default preamble for type '{preamble_type}' not found")
        return None

    async def get_preamble(
        self, name: str, preamble_type: str = "resume_preamble"
    ) -> Optional[str]:
        """
        Get a preamble by name and type.

        Args:
            name: Name of the preamble
            preamble_type: Type of preamble (default: resume_preamble)

        Returns:
            Preamble content if found, None otherwise
        """
        preamble = await self.preamble_repository.get_by_name(name, preamble_type)
        if preamble:
            return preamble.content
        self.logger.warning(f"Preamble '{name}' of type '{preamble_type}' not found")
        return None

    # Cache management
    def clear_caches(self) -> None:
        """Clear all repository caches."""
        self.header_repository.clear_cache()
        self.template_repository.clear_cache()
        self.preamble_repository.clear_cache()
        self.logger.debug("All TeX caches cleared")

    async def generate_resume_latex(
        self,
        resume: Resume,
        profile: Optional[Profile] = None,
        portfolio: Optional[Portfolio] = None,
    ) -> str:
        """
        Generate LaTeX code for a resume.

        Args:
            resume: Resume data
            profile: Profile data
            portfolio: Portfolio data

        Returns:
            str: LaTeX code
        """
        # Implementation details for generating resume LaTeX
        # ...
        pass

    async def generate_cover_letter_latex(
        self,
        cover_letter: Union[
            CoverLetter, Resume
        ],  # Support both CoverLetter and old Resume models
        profile: Profile,
        portfolio: Optional[Portfolio] = None,
    ) -> str:
        """
        Generate LaTeX code for a cover letter.

        Args:
            cover_letter: Cover letter data or Resume with cover letter
            profile: Profile data
            portfolio: Portfolio data

        Returns:
            str: LaTeX code
        """
        try:
            # Determine if we're using a Resume or CoverLetter model
            using_resume_model = isinstance(cover_letter, Resume)

            # Get appropriate content based on model type
            if using_resume_model:
                # Legacy support for Resume model with is_cover_letter=True
                cover_letter_text = cover_letter.cover_letter_content or ""
                company_name = cover_letter.company_name or ""
                job_title = cover_letter.job_title or ""
            else:
                # New CoverLetter model
                cover_letter_text = cover_letter.cover_letter_content or ""
                company_name = cover_letter.company_name or ""
                job_title = cover_letter.job_title or ""

            # Load template
            template = await self._get_template("cover_letter")

            # Load preamble
            preamble = await self._get_preamble()

            # Extract personal info from profile
            name = getattr(profile, "full_name", "")
            email = getattr(profile, "email", "")
            phone = getattr(profile, "phone", "")
            address = getattr(profile, "address", "")

            # Format date
            date = datetime.now(timezone.utc).strftime("%B %d, %Y")

            # Create LaTeX document
            latex = f"""
{preamble}

\\begin{{document}}

% Header
\\begin{{center}}
{{{name}}} \\\\
{email} | {phone} \\\\
{address} \\\\
\\end{{center}}

% Date
{date}

% Recipient
\\vspace{{1em}}
{company_name} \\\\
RE: {job_title} \\\\
\\vspace{{1em}}

% Salutation
Dear Hiring Manager,

% Content
\\vspace{{1em}}
{cover_letter_text}
\\vspace{{1em}}

% Closing
Sincerely,

\\vspace{{2em}}
{name}

\\end{{document}}
"""
            return latex

        except Exception as e:
            self.logger.error(f"Error generating cover letter LaTeX: {e}")
            raise

    async def compile_latex_to_pdf(self, latex: str) -> bytes:
        """
        Compile LaTeX to PDF.

        Args:
            latex: LaTeX code

        Returns:
            bytes: PDF content
        """
        # Implementation details for compiling LaTeX to PDF
        # ...
        pass

    async def _get_template(self, template_type: str) -> str:
        """
        Get a template.

        Args:
            template_type: Template type

        Returns:
            str: Template content
        """
        if not self.template_repository:
            # Return a default template if no repository available
            if template_type == "cover_letter":
                return """\\documentclass[11pt]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{hyperref}
\\begin{document}
{content}
\\end{document}"""
            else:
                return """\\documentclass[11pt]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{hyperref}
\\begin{document}
{content}
\\end{document}"""

        # Get template from repository
        template = await self.template_repository.get_by_type(template_type)
        if not template:
            self.logger.warning(f"Template {template_type} not found")
            return ""

        return template.content

    async def _get_preamble(self) -> str:
        """
        Get a preamble.

        Returns:
            str: Preamble content
        """
        if not self.preamble_repository:
            # Return a default preamble if no repository available
            return """\\documentclass[11pt]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{hyperref}"""

        # Get preamble from repository
        preamble = await self.preamble_repository.get_default()
        if not preamble:
            self.logger.warning("Default preamble not found")
            return """\\documentclass[11pt]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{hyperref}"""

        return preamble.content
