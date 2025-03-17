# Testing is done - Successful
import logging
from typing import Optional

from core.models.tex_header import TexHeader
from core.models.tex_template import TexTemplate

logger = logging.getLogger(__name__)


class TexLoader:
    """A class for loading LaTeX template files."""

    def __init__(self):
        """Initialize the TexLoader."""
        self.logger = logging.getLogger(__name__)
        self._cached_templates = {}

    async def get_template(self, name: str) -> Optional[TexTemplate]:
        """Get a template by name.

        Args:
            name: The name of the template to retrieve.

        Returns:
            Optional[TexTemplate]: The template if found, None otherwise.
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

    async def get_header(self, name: str) -> Optional[TexHeader]:
        """Get a header by name.

        Args:
            name: The name of the header to retrieve.

        Returns:
            Optional[TexHeader]: The header if found, None otherwise.
        """
        try:
            # Find header in database
            header = await TexHeader.find_one(TexHeader.name == name)
            if header:
                return header

            self.logger.warning(f"Header '{name}' not found in the database")
            return None

        except Exception as e:
            self.logger.error(f"Error retrieving header '{name}': {str(e)}")
            return None

    def safe_format_template(self, template: TexTemplate, **kwargs) -> str:
        """Safely format a template with the given parameters.

        Args:
            template: The template to format.
            **kwargs: The parameters to format the template with.

        Returns:
            str: The formatted template.

        Raises:
            ValueError: If formatting fails.
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


if __name__ == "__main__":
    tex_loader = TexLoader()
    print(tex_loader.get_template("personal_information"))
