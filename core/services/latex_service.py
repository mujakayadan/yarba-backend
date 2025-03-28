"""LaTeX service for LaTeX document generation."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from beanie import PydanticObjectId
from bson import json_util

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import InternalServerException
from core.latex.compilers import CoverLetterCompiler, ResumeCompiler
from core.latex.utils.placeholder import PlaceholderManager
from core.latex.utils.sanitizer import sanitize_latex
from core.models.cover_letter import CoverLetter
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository

settings = Settings()
logger = get_logger(__name__)


class LatexService:
    """Unified service for all LaTeX operations."""

    def __init__(
        self,
        preamble_repository: PreambleRepository,
        header_repository: TexHeaderRepository,
        template_repository: TexTemplateRepository,
    ):
        """
        Initialize LaTeX service.

        Args:
            preamble_repository: Repository for LaTeX preambles
            header_repository: Repository for LaTeX headers
            template_repository: Repository for LaTeX templates
        """
        self.preamble_repository = preamble_repository
        self.header_repository = header_repository
        self.template_repository = template_repository
        self.logger = logger
        self.placeholder_manager = PlaceholderManager()

        # Initialize compilers directly from the LaTeX module
        self.resume_compiler = ResumeCompiler()
        self.cover_letter_compiler = CoverLetterCompiler()

    # ===============================
    # Template Methods
    # ===============================

    async def get_template(self, template_name: str) -> Optional[str]:
        """
        Get a template by name.

        Args:
            template_name: Name of the template

        Returns:
            Template content if found, None otherwise
        """
        try:
            template = await self.template_repository.get_by_name(template_name)
            if not template:
                self.logger.warning(f"Template '{template_name}' not found")
                return None
            return template.content
        except Exception as e:
            self.logger.error(f"Error getting template {template_name}: {e}")
            return None

    async def get_template_by_type(self, template_type: str) -> Optional[str]:
        """
        Get a template by type.

        Args:
            template_type: Type of the template

        Returns:
            Template content if found, None otherwise
        """
        try:
            template = await self.template_repository.get_by_type(template_type)
            if not template:
                self.logger.warning(f"Template type '{template_type}' not found")
                return None
            return template.content
        except Exception as e:
            self.logger.error(f"Error getting template type {template_type}: {e}")
            return None

    async def get_all_templates(self) -> List[Dict[str, Any]]:
        """
        Get all templates.

        Returns:
            List of dictionaries with template information
        """
        try:
            templates = await self.template_repository.get_all()
            return [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "type": t.type,
                    "description": t.description,
                }
                for t in templates
            ]
        except Exception as e:
            self.logger.error(f"Error getting all templates: {e}")
            return []

    # ===============================
    # Header Methods
    # ===============================

    async def get_header(self, header_name: str = "default") -> Optional[str]:
        """
        Get a header by name.

        Args:
            header_name: Name of the header

        Returns:
            Header content if found, None otherwise
        """
        try:
            header = await self.header_repository.get_by_name(header_name)
            if not header:
                self.logger.warning(f"Header '{header_name}' not found")
                return None
            return header.content
        except Exception as e:
            self.logger.error(f"Error getting header {header_name}: {e}")
            return None

    async def get_headers_by_category(self, category: str) -> List[Dict[str, str]]:
        """
        Get all headers for a specific category.

        Args:
            category: Category of headers to get

        Returns:
            List of dictionaries with header information
        """
        try:
            headers = await self.header_repository.get_all_by_category(category)
            return [
                {
                    "id": str(h.id),
                    "name": h.name,
                    "category": h.category,
                    "content": h.content,
                }
                for h in headers
            ]
        except Exception as e:
            self.logger.error(f"Error getting headers for category {category}: {e}")
            return []

    async def get_header_names_by_category(self, category: str) -> List[str]:
        """
        Get all header names for a specific category.

        Args:
            category: Category of headers to get

        Returns:
            List of header names
        """
        try:
            headers = await self.header_repository.get_all_by_category(category)
            return [h.name for h in headers]
        except Exception as e:
            self.logger.error(
                f"Error getting header names for category {category}: {e}"
            )
            return []

    # ===============================
    # Preamble Methods
    # ===============================

    async def get_default_preamble(self) -> str:
        """
        Get default LaTeX preamble.

        Returns:
            str: LaTeX preamble content
        """
        try:
            preamble = await self.preamble_repository.get_default()
            if not preamble:
                self.logger.warning("Default preamble not found, using empty string")
                return ""
            return preamble.content
        except Exception as e:
            self.logger.error(f"Error getting default preamble: {e}")
            return ""

    async def get_preamble(self, preamble_id: Optional[PydanticObjectId] = None) -> str:
        """
        Get LaTeX preamble by ID.

        Args:
            preamble_id: Preamble ID (optional)

        Returns:
            str: LaTeX preamble content
        """
        try:
            if not preamble_id:
                return await self.get_default_preamble()

            preamble = await self.preamble_repository.get_by_id(preamble_id)
            if not preamble:
                self.logger.warning(f"Preamble {preamble_id} not found, using default")
                return await self.get_default_preamble()
            return preamble.content
        except Exception as e:
            self.logger.error(f"Error getting preamble {preamble_id}: {e}")
            return await self.get_default_preamble()

    async def get_preamble_by_name(
        self, name: str, preamble_type: str = None
    ) -> Optional[str]:
        """
        Get a preamble by name and optional type.

        Args:
            name: Name of the preamble
            preamble_type: Type of preamble (optional)

        Returns:
            Preamble content if found, None otherwise
        """
        try:
            preamble = None
            if preamble_type:
                preamble = await self.preamble_repository.get_by_name(
                    name, preamble_type
                )
            else:
                preamble = await self.preamble_repository.get_by_name(name)

            if not preamble:
                self.logger.warning(f"Preamble '{name}' not found")
                return None
            return preamble.content
        except Exception as e:
            self.logger.error(f"Error getting preamble {name}: {e}")
            return None

    # ===============================
    # LaTeX Generation Methods
    # ===============================

    def _format_links(self, links: Dict[str, str]) -> str:
        """
        Format links for LaTeX.

        Args:
            links: Dictionary of links

        Returns:
            str: Formatted links
        """
        if not links:
            return ""

        formatted_links = []
        for name, url in links.items():
            if url:
                formatted_links.append(f"\\href{{{url}}}{{{name}}}")

        return " | ".join(formatted_links)

    async def generate_resume_latex(
        self,
        resume: Resume,
        profile: Profile,
    ) -> str:
        """
        Generate LaTeX for a resume.

        Args:
            resume: Resume model
            profile: Profile model

        Returns:
            str: LaTeX document
        """
        try:
            # Log input data types and IDs
            self.logger.info(f"Generating LaTeX for resume ID: {resume.id}")
            self.logger.info(f"Using profile ID: {profile.id}")

            # Get template and preamble
            template = await self.get_template("resume") or ""
            preamble = await self.get_default_preamble()

            # Get header based on template_id or default
            header_name = resume.template_id if resume.template_id else "default"
            header = await self.get_header(header_name) or ""
            self.logger.debug(f"Using header: {header_name}")

            # Extract content from resume, ensure all MongoDB types are properly serialized
            content = resume.content or {}
            self.logger.debug(f"Resume content keys: {list(content.keys())}")

            # Create safe representations of all data by using json_util
            safe_resume_data = json_util.loads(
                json_util.dumps(
                    {
                        "id": resume.id,
                        "title": resume.title,
                        "template_id": resume.template_id,
                        "user_id": resume.user_id,
                        "profile_id": resume.profile_id,
                        "portfolio_id": resume.portfolio_id,
                        "content": content,
                    }
                )
            )

            safe_profile_data = json_util.loads(
                json_util.dumps(
                    {
                        "id": profile.id,
                        "full_name": profile.full_name,
                        "email": profile.email,
                        "phone": profile.phone,
                        "address": profile.address,
                        "linkedin": profile.linkedin,
                        "github": profile.github,
                        "website": profile.website,
                    }
                )
            )

            self.logger.debug(
                f"Serialized resume data: {safe_resume_data['id']}, title: {safe_resume_data['title']}"
            )
            self.logger.debug(
                f"Serialized profile data: {safe_profile_data['id']}, name: {safe_profile_data['full_name']}"
            )

            # Use the resume compiler from the LaTeX module
            template_data = {
                "header": {
                    "font_size": "11pt",
                    "document_class": "article",
                    "margin_size": "1in",
                    "packages": [
                        "geometry",
                        "hyperref",
                        "titlesec",
                        "enumitem",
                        "fancyhdr",
                    ],
                    "custom_commands": {},
                },
                "section_formats": {
                    "header": header,
                },
            }

            # Create a safe profile dict
            safe_profile = {
                "full_name": safe_profile_data["full_name"],
                "email": safe_profile_data["email"],
                "phone": safe_profile_data["phone"],
                "address": safe_profile_data["address"],
                "linkedin": safe_profile_data["linkedin"],
                "github": safe_profile_data["github"],
            }
            self.logger.debug(f"Profile data for LaTeX: {safe_profile}")

            # Create a resume object suitable for the compiler with safe references
            self.logger.debug("Creating compiler resume object")
            compiler_resume = Resume(
                id=safe_resume_data["id"],
                personal_information={
                    "name": safe_profile["full_name"],
                    "email": safe_profile["email"],
                    "phone": safe_profile["phone"],
                    "address": safe_profile["address"],
                    "linkedin": safe_profile["linkedin"],
                    "github": safe_profile["github"],
                },
                career_summary=safe_resume_data["content"].get("career_summary", ""),
                skills=safe_resume_data["content"].get("skills", ""),
                work_experience=safe_resume_data["content"].get("work_experience", ""),
                education=safe_resume_data["content"].get("education", ""),
            )

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling resume compiler to generate tex content")
            latex_content = await self.resume_compiler.generate_tex_content(
                compiler_resume, template_data
            )

            # Log success and content length
            self.logger.info(
                f"Successfully generated LaTeX content, length: {len(latex_content)} bytes"
            )
            return latex_content

        except Exception as e:
            self.logger.error(f"Error generating resume LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    async def generate_cover_letter_latex(
        self,
        cover_letter: Union[CoverLetter, Resume],
        profile: Profile,
    ) -> str:
        """
        Generate LaTeX for a cover letter.

        Args:
            cover_letter: Cover letter model or Resume model containing cover letter
            profile: Profile model

        Returns:
            str: LaTeX document
        """
        try:
            self.logger.info(f"Generating LaTeX for cover letter ID: {cover_letter.id}")
            self.logger.info(f"Using profile ID: {profile.id}")

            # Get template and preamble
            template = await self.get_template("cover_letter") or ""
            preamble = await self.get_default_preamble()

            # Get header based on template_id or default
            if isinstance(cover_letter, CoverLetter):
                header_name = (
                    cover_letter.template_id if cover_letter.template_id else "default"
                )
                cover_letter_text = cover_letter.cover_letter_content or ""
                company_name = cover_letter.company_name or ""
                job_title = cover_letter.job_title or ""
            else:  # Resume with cover letter
                header_name = (
                    cover_letter.template_id if cover_letter.template_id else "default"
                )
                cover_letter_text = cover_letter.cover_letter_content or ""
                company_name = cover_letter.company_name or ""
                job_title = cover_letter.job_title or ""

            self.logger.debug(f"Using header: {header_name}")
            self.logger.debug(f"Company: {company_name}, Job title: {job_title}")

            header = await self.get_header(header_name) or ""

            # Use json_util to safely serialize the data
            safe_cover_letter_data = json_util.loads(
                json_util.dumps(
                    {
                        "id": cover_letter.id,
                        "template_id": header_name,
                        "cover_letter_content": cover_letter_text,
                        "company_name": company_name,
                        "job_title": job_title,
                    }
                )
            )

            safe_profile_data = json_util.loads(
                json_util.dumps(
                    {
                        "id": profile.id,
                        "full_name": profile.full_name,
                        "email": profile.email,
                        "phone": profile.phone,
                        "address": profile.address,
                    }
                )
            )

            self.logger.debug(
                f"Serialized cover letter data: {safe_cover_letter_data['id']}"
            )
            self.logger.debug(f"Serialized profile data: {safe_profile_data['id']}")

            # Use the cover letter compiler from the LaTeX module
            template_data = {
                "header": {
                    "font_size": "11pt",
                    "document_class": "article",
                    "margin_size": "1in",
                    "packages": [
                        "geometry",
                        "hyperref",
                        "titlesec",
                        "enumitem",
                        "fancyhdr",
                    ],
                    "custom_commands": {},
                },
                "section_formats": {
                    "header": header,
                },
            }

            # Create a resume object suitable for the compiler
            self.logger.debug("Creating compiler cover letter object")
            compiler_resume = Resume(
                id=safe_cover_letter_data["id"],
                personal_information={
                    "name": safe_profile_data["full_name"],
                    "email": safe_profile_data["email"],
                    "phone": safe_profile_data["phone"],
                    "address": safe_profile_data["address"],
                    "recipient": {
                        "name": "Hiring Manager",
                        "title": "Hiring Manager",
                        "company": safe_cover_letter_data["company_name"],
                        "address": "",
                    },
                },
                cover_letter_content=safe_cover_letter_data["cover_letter_content"],
            )

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling cover letter compiler to generate tex content")
            latex_content = await self.cover_letter_compiler.generate_tex_content(
                compiler_resume, template_data
            )

            self.logger.info(
                f"Successfully generated cover letter LaTeX, length: {len(latex_content)} bytes"
            )
            return latex_content

        except Exception as e:
            self.logger.error(f"Error generating cover letter LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    # ===============================
    # PDF Compilation Methods
    # ===============================

    async def compile_latex_to_pdf(
        self, latex_content: str, is_cover_letter: bool = False
    ) -> bytes:
        """
        Compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX content
            is_cover_letter: Whether the content is for a cover letter

        Returns:
            bytes: PDF content

        Raises:
            InternalServerException: If compilation fails
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = settings.latex.output_dir
            self.logger.info(f"Using output directory: {output_dir.absolute()}")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create a unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            document_type = "cover_letter" if is_cover_letter else "resume"
            filename = f"{document_type}_{timestamp}"

            # Print the first few lines of LaTeX content for debugging
            content_preview = "\n".join(latex_content.split("\n")[:20]) + "\n..."
            self.logger.debug(f"LaTeX content preview:\n{content_preview}")

            # Save LaTeX content for debugging
            tex_path = output_dir / f"{filename}.tex"
            self.logger.info(f"Saving LaTeX content to {tex_path.absolute()}")
            tex_path.write_text(latex_content)
            self.logger.info(
                f"LaTeX content saved successfully to {tex_path.absolute()}"
            )

            # Create a temp directory for compilation that's not deleted immediately
            temp_dir = output_dir / "temp" / timestamp
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Using temporary directory: {temp_dir.absolute()}")

            # Create temporary file path
            temp_tex_path = temp_dir / "document.tex"
            self.logger.info(
                f"Writing LaTeX content to temporary file: {temp_tex_path.absolute()}"
            )
            temp_tex_path.write_text(latex_content)

            # Use the appropriate compiler based on document type
            compiler = (
                self.cover_letter_compiler if is_cover_letter else self.resume_compiler
            )

            # Update compiler settings from the application settings
            compiler.compiler_path = settings.latex.compiler_path
            compiler.compiler_options = settings.latex.compiler_options
            compiler.cleanup_temp_files = False  # Keep temporary files for debugging
            compiler.temp_extensions = settings.latex.temp_extensions

            self.logger.info(f"Using compiler: {compiler.__class__.__name__}")
            self.logger.info(f"Compiler path: {compiler.compiler_path}")
            self.logger.info(f"Compiler options: {compiler.compiler_options}")

            # Compile the LaTeX content
            self.logger.info(f"Starting PDF compilation for {document_type}")
            pdf_content = await compiler.compile_pdf(temp_tex_path, latex_content)

            if pdf_content is None:
                error_message = f"LaTeX compilation failed for {document_type}"
                self.logger.error(error_message)
                # Check if log file exists and print it
                log_file = temp_dir / "document.log"
                if log_file.exists():
                    self.logger.error(
                        f"LaTeX log file content:\n{log_file.read_text()}"
                    )
                raise InternalServerException(error_message)

            # Save PDF content for debugging
            pdf_path = output_dir / f"{filename}.pdf"
            self.logger.info(f"Saving PDF content to {pdf_path.absolute()}")
            pdf_path.write_bytes(pdf_content)
            self.logger.info(
                f"PDF content saved successfully to {pdf_path.absolute()}, size: {len(pdf_content)} bytes"
            )

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error compiling LaTeX: {e}")
            # Print full traceback for debugging
            import traceback

            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise InternalServerException(f"Error compiling LaTeX: {str(e)}")

    # ===============================
    # Cache Management
    # ===============================

    async def clear_caches(self) -> None:
        """Clear all repository caches."""
        await self.template_repository.clear_cache()
        await self.header_repository.clear_cache()
        await self.preamble_repository.clear_cache()


def get_latex_service() -> LatexService:
    """
    Get a new instance of LatexService with default repositories.

    Returns:
        LatexService: A new instance of LatexService
    """
    from core.repositories.preamble_repository import get_preamble_repository
    from core.repositories.tex_header_repository import get_tex_header_repository
    from core.repositories.tex_template_repository import get_tex_template_repository

    return LatexService(
        preamble_repository=get_preamble_repository(),
        header_repository=get_tex_header_repository(),
        template_repository=get_tex_template_repository(),
    )
