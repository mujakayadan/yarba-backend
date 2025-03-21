"""TeX template repository implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from core.models.tex_template import TexTemplate
from core.repositories.base_repository import BeanieRepository


class TexTemplateRepository(BeanieRepository[TexTemplate]):
    """Repository for TeX templates with caching support."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(TexTemplate)
        self._cached_templates: Dict[str, TexTemplate] = {}
        self.logger = get_logger(__name__)

    async def get_by_name(self, name: str) -> Optional[TexTemplate]:
        """
        Get a template by name with caching.

        Args:
            name: Name of the template

        Returns:
            TexTemplate if found, None otherwise
        """
        try:
            # Use cached template if available
            if name in self._cached_templates:
                return self._cached_templates[name]

            # Find template in database
            template = await TexTemplate.find_one(TexTemplate.name == name)
            if template:
                # Cache the template for future use
                self._cached_templates[name] = template
                return template

            self.logger.warning(f"Template '{name}' not found in the database")
            return None

        except Exception as e:
            self.logger.error(f"Error retrieving template '{name}': {str(e)}")
            return None

    def safe_format_template(self, template: TexTemplate, **kwargs) -> str:
        """
        Safely format a template with the given parameters.

        Args:
            template: The template to format
            **kwargs: The parameters to format the template with

        Returns:
            str: The formatted template

        Raises:
            ValueError: If formatting fails
        """
        try:
            return template.to_latex(**kwargs)
        except KeyError as e:
            self.logger.error(f"KeyError in template '{template.name}': {e}")
            raise ValueError(f"Missing key in template '{template.name}': {e}")
        except ValueError as e:
            self.logger.error(f"ValueError in template '{template.name}': {e}")
            raise ValueError(f"Error formatting template '{template.name}': {e}")

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cached_templates.clear()
        self.logger.debug("Template cache cleared")

    async def create_template(
        self,
        name: str,
        content: str,
        template_type: str = "resume",
        is_default: bool = False,
    ) -> TexTemplate:
        """
        Create a new TeX template.

        Args:
            name: Name of the template
            content: LaTeX code content
            template_type: Type of template (default: resume)
            is_default: Whether this is a default template (default: False)

        Returns:
            Created template
        """
        template = TexTemplate(
            name=name,
            content=content,
            type=template_type,
            is_default=is_default,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await template.create()
        return template

    async def get_all_by_type(self, template_type: str = "resume") -> List[TexTemplate]:
        """
        Get all templates of a specific type.

        Args:
            template_type: Type of templates to get (default: resume)

        Returns:
            List of templates
        """
        return await TexTemplate.find({"type": template_type}).to_list()

    async def get_default(self, template_type: str = "resume") -> Optional[TexTemplate]:
        """
        Get the default template for a specific type.

        Args:
            template_type: Type of template to get the default for (default: resume)

        Returns:
            The default template if found, None otherwise
        """
        template = await TexTemplate.find_one(
            {"type": template_type, "is_default": True}
        )
        if template:
            self._cached_templates[template.name] = template
        return template

    async def update_content(
        self, template_id: str, content: str
    ) -> Optional[TexTemplate]:
        """
        Update the content of a template.

        Args:
            template_id: ID of the template to update
            content: New LaTeX code content

        Returns:
            Updated template if found, None otherwise
        """
        template = await TexTemplate.get(template_id)
        if not template:
            return None

        template.content = content
        template.updated_at = datetime.utcnow()
        await template.save()

        # Update cache if template is in cache
        if template.name in self._cached_templates:
            self._cached_templates[template.name] = template

        return template


# Factory function for dependency injection
def get_tex_template_repository() -> TexTemplateRepository:
    """
    Factory function to create a TeX template repository instance.

    Returns:
        TexTemplateRepository: A new instance of the TeX template repository
    """
    return TexTemplateRepository()
