"""TeX header repository implementation with support for different component types."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from config.logging_config import get_logger
from core.models.tex_header import TexHeader
from core.repositories.base_repository import BeanieRepository


class TexHeaderRepository(BeanieRepository[TexHeader]):
    """Repository for TeX headers with caching support and component type handling."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(TexHeader)
        self._cached_headers: Dict[str, TexHeader] = {}
        self.logger = get_logger(__name__)

    async def get_by_name(self, name: str) -> Optional[TexHeader]:
        """
        Get a header by name with caching.

        Args:
            name: Name of the header

        Returns:
            TexHeader if found, None otherwise
        """
        try:
            # Use cached header if available
            if name in self._cached_headers:
                return self._cached_headers[name]

            # Find header in database
            header = await TexHeader.find_one(TexHeader.name == name)
            if header:
                # Cache the header for future use
                self._cached_headers[name] = header
                return header

            self.logger.warning(f"Header '{name}' not found in the database")
            return None

        except Exception as e:
            self.logger.error(f"Error retrieving header '{name}': {str(e)}")
            return None

    async def get_all_by_category(self, category: str) -> List[TexHeader]:
        """
        Get all headers of a specific category.

        Args:
            category: Category of headers to get (e.g., resume_section, template, preamble)

        Returns:
            List of headers
        """
        return await TexHeader.find(TexHeader.category == category).to_list()

    async def get_all_by_category_and_default(
        self, category: str, is_default: bool = True
    ) -> List[TexHeader]:
        """
        Get all headers of a specific category with specified default status.

        Args:
            category: Category of headers to get
            is_default: Whether to get default headers (True) or non-default headers (False)

        Returns:
            List of matching headers
        """
        return await TexHeader.find(
            {"category": category, "is_default": is_default}
        ).to_list()

    async def get_resume_sections(
        self, is_default: Optional[bool] = None
    ) -> List[TexHeader]:
        """
        Get all resume section headers.

        Args:
            is_default: Filter by default status (None for all)

        Returns:
            List of resume section headers
        """
        query = {"category": "resume_section"}
        if is_default is not None:
            query["is_default"] = is_default
        return await TexHeader.find(query).to_list()

    async def get_resume_items(
        self, is_default: Optional[bool] = None
    ) -> List[TexHeader]:
        """
        Get all resume item headers.

        Args:
            is_default: Filter by default status (None for all)

        Returns:
            List of resume item headers
        """
        query = {"category": "resume_item"}
        if is_default is not None:
            query["is_default"] = is_default
        return await TexHeader.find(query).to_list()

    async def get_default(
        self, category: str = "resume_section"
    ) -> Optional[TexHeader]:
        """
        Get the default header for a specific category.

        Args:
            category: Category of header to get the default for

        Returns:
            The default header if found, None otherwise
        """
        header = await TexHeader.find_one({"category": category, "is_default": True})
        if header:
            self._cached_headers[header.name] = header
        return header

    async def get_template(self, name: str) -> Optional[TexHeader]:
        """
        Get a template (special category of header) by name.

        Args:
            name: Name of the template

        Returns:
            TexHeader if found, None otherwise
        """
        try:
            # Just get by name but log appropriately for templates
            template = await self.get_by_name(name)
            if not template:
                self.logger.warning(f"Template '{name}' not found in the database")
            return template
        except Exception as e:
            self.logger.error(f"Error retrieving template '{name}': {str(e)}")
            return None

    async def get_all_templates(
        self, is_default: Optional[bool] = None
    ) -> List[TexHeader]:
        """
        Get all available templates.

        Args:
            is_default: Filter by default status (None for all)

        Returns:
            List of template headers
        """
        query = {"category": "template"}
        if is_default is not None:
            query["is_default"] = is_default
        return await TexHeader.find(query).to_list()

    def format_tex_content(self, header: TexHeader, **kwargs) -> str:
        """
        Safely format a header's content with the given parameters.

        Args:
            header: The header to format
            **kwargs: The parameters to format the content with

        Returns:
            str: The formatted content

        Raises:
            ValueError: If formatting fails
        """
        try:
            return header.content.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"KeyError in header '{header.name}': {e}")
            raise ValueError(f"Missing key in header '{header.name}': {e}")
        except ValueError as e:
            self.logger.error(f"ValueError in header '{header.name}': {e}")
            raise ValueError(f"Error formatting header '{header.name}': {e}")

    async def clear_cache(self) -> None:
        """Clear the header cache."""
        self._cached_headers.clear()
        self.logger.debug("Header cache cleared")

    async def create_header(
        self,
        name: str,
        content: str,
        category: str = "resume_section",
        is_default: bool = False,
    ) -> TexHeader:
        """
        Create a new TeX header.

        Args:
            name: Name of the header
            content: LaTeX code content
            category: Category of the header (default: resume_section)
            is_default: Whether this is a default header (default: False)

        Returns:
            Created header
        """
        header = TexHeader(
            name=name,
            content=content,
            category=category,
            is_default=is_default,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await header.create()
        return header

    async def update_content(self, header_id: str, content: str) -> Optional[TexHeader]:
        """
        Update the content of a header.

        Args:
            header_id: ID of the header to update
            content: New LaTeX code content

        Returns:
            Updated header if found, None otherwise
        """
        header = await TexHeader.get(header_id)
        if not header:
            return None

        header.content = content
        header.updated_at = datetime.now(timezone.utc)
        await header.save()

        # Update cache if header is in cache
        if header.name in self._cached_headers:
            self._cached_headers[header.name] = header

        return header

    async def update_header(
        self, header_id: str, data: Dict[str, Any]
    ) -> Optional[TexHeader]:
        """
        Update multiple fields of a header.

        Args:
            header_id: ID of the header to update
            data: Dictionary of fields to update (can include content, name, category, is_default)

        Returns:
            Updated header if found, None otherwise
        """
        header = await TexHeader.get(header_id)
        if not header:
            self.logger.warning(f"Header with ID '{header_id}' not found for update")
            return None

        # Update fields
        for key, value in data.items():
            if hasattr(header, key):
                setattr(header, key, value)

        header.updated_at = datetime.now(timezone.utc)
        await header.save()

        # Update cache if header is in cache
        if header.name in self._cached_headers:
            self._cached_headers[header.name] = header

        return header

    async def delete_header(self, header_id: str) -> bool:
        """
        Delete a header by ID.

        Args:
            header_id: ID of the header to delete

        Returns:
            True if deleted, False if not found
        """
        header = await TexHeader.get(header_id)
        if not header:
            self.logger.warning(f"Header with ID '{header_id}' not found for deletion")
            return False

        # Remove from cache if present
        if header.name in self._cached_headers:
            del self._cached_headers[header.name]

        await header.delete()
        return True

    async def delete_by_name(self, name: str) -> bool:
        """
        Delete a header by name.

        Args:
            name: Name of the header to delete

        Returns:
            True if deleted, False if not found
        """
        header = await TexHeader.find_one(TexHeader.name == name)
        if not header:
            self.logger.warning(f"Header with name '{name}' not found for deletion")
            return False

        # Remove from cache if present
        if name in self._cached_headers:
            del self._cached_headers[name]

        await header.delete()
        return True

    async def set_default_status(
        self, header_id: str, is_default: bool = True
    ) -> Optional[TexHeader]:
        """
        Set the default status of a header.
        If setting to default (True), this will unset any other default
        in the same category.

        Args:
            header_id: ID of the header to update
            is_default: New default status

        Returns:
            Updated header if found, None otherwise
        """
        header = await TexHeader.get(header_id)
        if not header:
            self.logger.warning(f"Header with ID '{header_id}' not found")
            return None

        # If setting as default, unset other defaults in the same category
        if is_default:
            # Find current default header in the same category
            current_default = await TexHeader.find_one(
                {"category": header.category, "is_default": True}
            )

            # If there's a different default header, unset it
            if current_default and str(current_default.id) != header_id:
                current_default.is_default = False
                current_default.updated_at = datetime.now(timezone.utc)
                await current_default.save()

                # Update cache if needed
                if current_default.name in self._cached_headers:
                    self._cached_headers[current_default.name] = current_default

        # Update the target header
        header.is_default = is_default
        header.updated_at = datetime.now(timezone.utc)
        await header.save()

        # Update cache
        if header.name in self._cached_headers:
            self._cached_headers[header.name] = header

        return header

    async def clone_header(
        self, source_id: str, new_name: str, is_default: bool = False
    ) -> Optional[TexHeader]:
        """
        Clone an existing header with a new name.

        Args:
            source_id: ID of the header to clone
            new_name: Name for the new header
            is_default: Whether the new header should be default

        Returns:
            The newly created header if successful, None otherwise
        """
        source = await TexHeader.get(source_id)
        if not source:
            self.logger.warning(
                f"Source header with ID '{source_id}' not found for cloning"
            )
            return None

        # Check if a header with new_name already exists
        existing = await TexHeader.find_one(TexHeader.name == new_name)
        if existing:
            self.logger.warning(f"Header with name '{new_name}' already exists")
            return None

        # Create the new header
        return await self.create_header(
            name=new_name,
            content=source.content,
            category=source.category,
            is_default=is_default,
        )

    async def get_by_query(self, query: Dict[str, Any]) -> List[TexHeader]:
        """
        Get headers by arbitrary query criteria.

        Args:
            query: Dictionary with query parameters

        Returns:
            List of matching headers
        """
        return await TexHeader.find(query).to_list()

    async def bulk_create_or_update(
        self, headers: List[Dict[str, Any]]
    ) -> List[TexHeader]:
        """
        Create or update multiple headers in a batch.

        Args:
            headers: List of header dictionaries with at least 'name' and 'content'

        Returns:
            List of created/updated headers
        """
        result = []

        for header_data in headers:
            name = header_data.get("name")
            if not name:
                self.logger.warning("Skipping header with no name in bulk operation")
                continue

            # Check if header exists
            existing = await TexHeader.find_one(TexHeader.name == name)

            if existing:
                # Update existing header
                for key, value in header_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)

                existing.updated_at = datetime.now(timezone.utc)
                await existing.save()

                # Update cache
                if name in self._cached_headers:
                    self._cached_headers[name] = existing

                result.append(existing)
            else:
                # Create new header
                category = header_data.get("category", "resume_section")
                content = header_data.get("content", "")
                is_default = header_data.get("is_default", False)

                new_header = await self.create_header(
                    name=name,
                    content=content,
                    category=category,
                    is_default=is_default,
                )

                result.append(new_header)

        return result

    async def search_headers(
        self,
        text: str,
        categories: Optional[List[str]] = None,
        is_default: Optional[bool] = None,
    ) -> List[TexHeader]:
        """
        Search for headers containing specific text in name or content.

        Args:
            text: Text to search for
            categories: Optional list of categories to limit search to
            is_default: Optional filter for default status

        Returns:
            List of matching headers
        """
        query = {
            "$or": [
                {"name": {"$regex": text, "$options": "i"}},
                {"content": {"$regex": text, "$options": "i"}},
            ]
        }

        if categories:
            query["category"] = {"$in": categories}

        if is_default is not None:
            query["is_default"] = is_default

        return await TexHeader.find(query).to_list()

    # Factory methods for creating specific types
    async def create_template(
        self,
        name: str,
        content: str,
        is_default: bool = False,
    ) -> TexHeader:
        """
        Create a new TeX template (special category of header).

        Args:
            name: Name of the template
            content: LaTeX code content
            is_default: Whether this is a default template (default: False)

        Returns:
            Created template
        """
        return await self.create_header(
            name=name, content=content, category="template", is_default=is_default
        )

    async def create_resume_section(
        self,
        name: str,
        content: str,
        is_default: bool = False,
    ) -> TexHeader:
        """
        Create a new resume section header.

        Args:
            name: Name of the section
            content: LaTeX code content
            is_default: Whether this is a default section (default: False)

        Returns:
            Created header
        """
        return await self.create_header(
            name=name, content=content, category="resume_section", is_default=is_default
        )

    async def create_resume_item(
        self,
        name: str,
        content: str,
        is_default: bool = False,
    ) -> TexHeader:
        """
        Create a new resume item header.

        Args:
            name: Name of the item
            content: LaTeX code content
            is_default: Whether this is a default item (default: False)

        Returns:
            Created header
        """
        return await self.create_header(
            name=name, content=content, category="resume_item", is_default=is_default
        )


# Factory function for dependency injection
def get_tex_header_repository() -> TexHeaderRepository:
    """
    Factory function to create a TeX header repository instance.

    Returns:
        TexHeaderRepository: A new instance of the TeX header repository
    """
    return TexHeaderRepository()
