"""LaTeX service for LaTeX document generation."""

import json
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from beanie import PydanticObjectId
from bson import ObjectId, json_util

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import InternalServerException, NotFoundException
from core.latex.compilers import CoverLetterCompiler, ResumeCompiler
from core.models.cover_letter import CoverLetter
from core.models.profile import Profile
from core.models.resume import Resume
from core.models.tex_header import TexHeader
from core.repositories.preamble_repository import (
    PreambleRepository,
    get_preamble_repository,
)
from core.repositories.tex_header_repository import (
    TexHeaderRepository,
    get_tex_header_repository,
)

settings = Settings()
logger = get_logger(__name__)


class LatexService:
    """Unified service for all LaTeX operations."""

    def __init__(
        self,
        preamble_repository: PreambleRepository,
        header_repository: TexHeaderRepository,
    ):
        """
        Initialize LaTeX service.

        Args:
            preamble_repository: Repository for LaTeX preambles
            header_repository: Repository for LaTeX headers
        """
        self.preamble_repository = preamble_repository
        self.header_repository = header_repository
        self.logger = logger

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

    async def get_default_header_by_category(
        self, category: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the default header for a specific category.

        Args:
            category: Category to get the default header for

        Returns:
            Dictionary with header information if found, None otherwise
        """
        try:
            header = await self.header_repository.get_default(category)
            if not header:
                self.logger.warning(
                    f"No default header found for category '{category}'"
                )
                return None

            return {
                "id": str(header.id),
                "name": header.name,
                "category": header.category,
                "content": header.content,
                "is_default": header.is_default,
            }
        except Exception as e:
            self.logger.error(
                f"Error getting default header for category {category}: {e}"
            )
            return None

    async def get_headers_by_category_and_default(
        self, category: str, is_default: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all headers for a specific category and default status.

        Args:
            category: Category of headers to get
            is_default: Whether to get default headers (True) or non-default (False)

        Returns:
            List of dictionaries with header information
        """
        try:
            headers = await self.header_repository.get_all_by_category_and_default(
                category, is_default
            )
            return [
                {
                    "id": str(h.id),
                    "name": h.name,
                    "category": h.category,
                    "content": h.content,
                    "is_default": h.is_default,
                }
                for h in headers
            ]
        except Exception as e:
            self.logger.error(
                f"Error getting headers for category {category} with default={is_default}: {e}"
            )
            return []

    async def get_resume_sections(
        self, is_default: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all resume section headers, optionally filtered by default status.

        Args:
            is_default: Filter by default status (None for all)

        Returns:
            List of dictionaries with header information
        """
        try:
            sections = await self.header_repository.get_resume_sections(is_default)
            return [
                {
                    "id": str(h.id),
                    "name": h.name,
                    "content": h.content,
                    "is_default": h.is_default,
                }
                for h in sections
            ]
        except Exception as e:
            self.logger.error(f"Error getting resume sections: {e}")
            return []

    async def get_resume_items(
        self, is_default: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all resume item headers, optionally filtered by default status.

        Args:
            is_default: Filter by default status (None for all)

        Returns:
            List of dictionaries with header information
        """
        try:
            items = await self.header_repository.get_resume_items(is_default)
            return [
                {
                    "id": str(h.id),
                    "name": h.name,
                    "content": h.content,
                    "is_default": h.is_default,
                }
                for h in items
            ]
        except Exception as e:
            self.logger.error(f"Error getting resume items: {e}")
            return []

    async def search_headers(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        is_default: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for headers by text in name or content.

        Args:
            query: Text to search for
            categories: Optional list of categories to search in
            is_default: Optional default status filter

        Returns:
            List of matching header dictionaries
        """
        try:
            headers = await self.header_repository.search_headers(
                query, categories, is_default
            )
            return [
                {
                    "id": str(h.id),
                    "name": h.name,
                    "category": h.category,
                    "content": h.content,
                    "is_default": h.is_default,
                }
                for h in headers
            ]
        except Exception as e:
            self.logger.error(f"Error searching headers with query '{query}': {e}")
            return []

    # ===============================
    # Header Management Methods
    # ===============================

    async def create_header(
        self,
        name: str,
        content: str,
        category: str = "resume_section",
        is_default: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new header.

        Args:
            name: Name of the header
            content: LaTeX content
            category: Header category
            is_default: Whether this is a default header

        Returns:
            Dictionary with the created header information
        """
        try:
            header = await self.header_repository.create_header(
                name=name,
                content=content,
                category=category,
                is_default=is_default,
            )

            return {
                "id": str(header.id),
                "name": header.name,
                "category": header.category,
                "content": header.content,
                "is_default": header.is_default,
            }
        except Exception as e:
            self.logger.error(f"Error creating header '{name}': {e}")
            raise InternalServerException(f"Failed to create header: {str(e)}")

    async def update_header(
        self, header_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a header's fields.

        Args:
            header_id: ID of the header to update
            data: Dictionary of fields to update

        Returns:
            Updated header information if successful, None otherwise
        """
        try:
            header = await self.header_repository.update_header(header_id, data)
            if not header:
                return None

            return {
                "id": str(header.id),
                "name": header.name,
                "category": header.category,
                "content": header.content,
                "is_default": header.is_default,
            }
        except Exception as e:
            self.logger.error(f"Error updating header {header_id}: {e}")
            raise InternalServerException(f"Failed to update header: {str(e)}")

    async def delete_header(self, header_id: str) -> bool:
        """
        Delete a header by ID.

        Args:
            header_id: ID of the header to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            return await self.header_repository.delete_header(header_id)
        except Exception as e:
            self.logger.error(f"Error deleting header {header_id}: {e}")
            raise InternalServerException(f"Failed to delete header: {str(e)}")

    async def clone_header(
        self, source_id: str, new_name: str, is_default: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Clone an existing header with a new name.

        Args:
            source_id: ID of the header to clone
            new_name: Name for the new header
            is_default: Whether the new header should be default

        Returns:
            Cloned header information if successful, None otherwise
        """
        try:
            header = await self.header_repository.clone_header(
                source_id, new_name, is_default
            )
            if not header:
                return None

            return {
                "id": str(header.id),
                "name": header.name,
                "category": header.category,
                "content": header.content,
                "is_default": header.is_default,
            }
        except Exception as e:
            self.logger.error(f"Error cloning header {source_id}: {e}")
            raise InternalServerException(f"Failed to clone header: {str(e)}")

    async def set_default_status(
        self, header_id: str, is_default: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Set the default status of a header.

        Args:
            header_id: ID of the header to update
            is_default: New default status

        Returns:
            Updated header information if successful, None otherwise
        """
        try:
            header = await self.header_repository.set_default_status(
                header_id, is_default
            )
            if not header:
                return None

            return {
                "id": str(header.id),
                "name": header.name,
                "category": header.category,
                "content": header.content,
                "is_default": header.is_default,
            }
        except Exception as e:
            self.logger.error(
                f"Error setting default status for header {header_id}: {e}"
            )
            raise InternalServerException(f"Failed to update default status: {str(e)}")

    async def bulk_create_or_update_headers(
        self, headers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create or update multiple headers in a batch.

        Args:
            headers: List of header dictionaries with at least 'name' and 'content'

        Returns:
            List of created/updated header information
        """
        try:
            results = await self.header_repository.bulk_create_or_update(headers)
            return [
                {
                    "id": str(h.id),
                    "name": h.name,
                    "category": h.category,
                    "content": h.content,
                    "is_default": h.is_default,
                }
                for h in results
            ]
        except Exception as e:
            self.logger.error(f"Error in bulk header operation: {e}")
            raise InternalServerException(
                f"Failed to complete bulk header operation: {str(e)}"
            )

    # ===============================
    # Template Header Methods
    # ===============================

    async def get_all_template_headers(
        self, is_default: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all template headers.

        Args:
            is_default: Filter by default status (None for all)

        Returns:
            List of template header dictionaries
        """
        try:
            templates = await self.header_repository.get_all_templates(is_default)
            return [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "content": t.content,
                    "is_default": t.is_default,
                }
                for t in templates
            ]
        except Exception as e:
            self.logger.error(f"Error getting template headers: {e}")
            return []

    async def create_template_header(
        self, name: str, content: str, is_default: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new template header.

        Args:
            name: Name of the template
            content: LaTeX content
            is_default: Whether this is a default template

        Returns:
            Dictionary with the created template information
        """
        try:
            template = await self.header_repository.create_template(
                name=name,
                content=content,
                is_default=is_default,
            )

            return {
                "id": str(template.id),
                "name": template.name,
                "category": template.category,
                "content": template.content,
                "is_default": template.is_default,
            }
        except Exception as e:
            self.logger.error(f"Error creating template header '{name}': {e}")
            raise InternalServerException(f"Failed to create template: {str(e)}")

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

            self.logger.debug(f"Found preamble '{name}' of type '{preamble_type}'")
            return preamble.content
        except Exception as e:
            self.logger.error(f"Error getting preamble {name}: {e}")
            return None

    # ===============================
    # LaTeX Generation Methods
    # ===============================

    async def _prepare_template_data(
        self, template_id: Optional[str] = None, document_type: str = "resume"
    ) -> Dict[str, Any]:
        """
        Prepare template data for document generation.

        Args:
            template_id: ID of template to use (optional)
            document_type: Type of document ('resume' or 'cover_letter')

        Returns:
            Template data dictionary
        """
        # Get preamble based on document type
        preamble_type = f"{document_type}_preamble"
        preamble = await self.get_preamble_by_name("default", preamble_type)

        if not preamble:
            self.logger.warning(
                f"{document_type.title()} preamble not found, using default"
            )
            preamble = await self.get_default_preamble()

        # Get header based on template_id or default
        header_name = template_id if template_id else "default"
        header = await self.get_header(header_name) or ""

        # Prepare template data structure
        return {
            "header": {
                "preamble": preamble,
            },
            "section_formats": {
                "header": header,
            },
        }

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
            # Log input data IDs
            self.logger.info(f"Generating LaTeX for resume ID: {resume.id}")
            self.logger.info(f"Using profile ID: {profile.id}")

            # Prepare template data with preamble and header
            template_data = await self._prepare_template_data(
                template_id=resume.template_id, document_type="resume"
            )

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling resume compiler to generate tex content")
            latex_content = await self.resume_compiler.generate_tex_content(
                resume=resume, template=template_data
            )

            self.logger.info(
                f"Successfully generated LaTeX content, length: {len(latex_content)} bytes"
            )

            return latex_content

        except Exception as e:
            self.logger.error(f"Error generating resume LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
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

            # Get template_id, company, job title based on input type
            if isinstance(cover_letter, CoverLetter):
                template_id = cover_letter.template_id
                cover_letter_text = cover_letter.cover_letter_content or ""
                company_name = cover_letter.company_name or ""
                job_title = cover_letter.job_title or ""
            else:  # Resume with cover letter
                template_id = cover_letter.template_id
                cover_letter_text = cover_letter.cover_letter_content or ""
                company_name = cover_letter.company_name or ""
                job_title = cover_letter.job_title or ""

            # Prepare template data
            template_data = await self._prepare_template_data(
                template_id=template_id, document_type="cover_letter"
            )

            # Create a compiler-compatible cover letter object
            self.logger.debug("Creating compiler cover letter object")
            try:
                # Create a compiler-compatible cover letter object
                compiler_cover_letter = CoverLetter(
                    id=cover_letter.id,
                    template_id=template_id,
                    cover_letter_content=cover_letter_text,
                    company_name=company_name,
                    job_title=job_title,
                )
                self.logger.debug(
                    f"Successfully created compiler cover letter object with ID: {compiler_cover_letter.id}"
                )
            except Exception as e:
                self.logger.error(f"Error creating compiler cover letter object: {e}")
                raise ValueError(f"Failed to create cover letter object: {e}")

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling cover letter compiler to generate tex content")
            latex_content = await self.cover_letter_compiler.generate_tex_content(
                compiler_cover_letter, template_data
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
            # Create output directory
            output_dir = settings.latex.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create unique filename and temp directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            document_type = "cover_letter" if is_cover_letter else "resume"
            filename = f"{document_type}_{timestamp}"

            # Create temp directory
            temp_dir = output_dir / "temp" / timestamp
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Log configuration
            self.logger.info(f"Compiling {document_type} in {temp_dir}")

            # Save LaTeX content to files
            tex_path = temp_dir / "document.tex"
            tex_path.write_text(latex_content)

            # Use appropriate compiler
            compiler = (
                self.cover_letter_compiler if is_cover_letter else self.resume_compiler
            )

            # Configure compiler
            compiler.compiler_path = settings.latex.compiler_path
            compiler.compiler_options = settings.latex.compiler_options
            compiler.cleanup_temp_files = False  # Keep temp files for debugging
            compiler.temp_extensions = settings.latex.temp_extensions

            # Compile to PDF
            self.logger.info(
                f"Starting PDF compilation with {compiler.__class__.__name__}"
            )
            pdf_content = await compiler.compile_pdf(tex_path, latex_content)

            # Handle compilation failure
            if pdf_content is None:
                log_file = temp_dir / "document.log"
                log_content = (
                    log_file.read_text() if log_file.exists() else "Log file not found"
                )
                error_msg = f"LaTeX compilation failed for {document_type}. Check log: {log_file}"
                self.logger.error(error_msg)
                self.logger.error(f"LaTeX log: {log_content}")
                raise InternalServerException(error_msg)

            # Save PDF output for reference
            pdf_path = output_dir / f"{filename}.pdf"
            pdf_path.write_bytes(pdf_content)
            self.logger.info(
                f"Compilation successful. PDF saved to {pdf_path} ({len(pdf_content)} bytes)"
            )

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error compiling LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise InternalServerException(f"Error compiling LaTeX: {str(e)}")

    # ===============================
    # Cache Management
    # ===============================

    async def clear_caches(self) -> None:
        """Clear all repository caches."""
        await self.header_repository.clear_cache()
        await self.preamble_repository.clear_cache()


def get_latex_service() -> LatexService:
    """
    Get a new instance of LatexService with default repositories.

    Returns:
        LatexService: A new instance of LatexService
    """
    return LatexService(
        preamble_repository=get_preamble_repository(),
        header_repository=get_tex_header_repository(),
    )
