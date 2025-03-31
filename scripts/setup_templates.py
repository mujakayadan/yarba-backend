#!/usr/bin/env python
"""
Script to check LaTeX templates in the database.
This script verifies that necessary templates exist without modifying them.
"""

import asyncio

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import get_logger
from config.settings import Settings
from core.models.tex_header import TexHeader
from core.repositories.tex_header_repository import TexHeaderRepository

settings = Settings()
logger = get_logger(__name__)

REQUIRED_SECTION_TEMPLATES = [
    "personal_information",
    "career_summary",
    "skills",
    "work_experience",
    "education",
    "projects",
    "awards",
    "publications",
]


async def check_template_exists(repository, name):
    """Check if a template exists in the database and log its details."""
    existing = await repository.get_by_name(name)

    if existing:
        logger.info(
            f"Template '{name}' exists with content: {existing.content[:50]}..."
        )
        return existing
    else:
        logger.warning(f"Template '{name}' not found in the database")
        return None


async def check_templates():
    """Check all necessary templates in the database."""
    # Initialize database connection
    client = AsyncIOMotorClient(settings.database.url)
    await init_beanie(
        database=client[settings.database.name],
        document_models=[TexHeader],
    )

    # Initialize repositories
    header_repo = TexHeaderRepository()

    # Check section templates
    for section_name in REQUIRED_SECTION_TEMPLATES:
        await check_template_exists(header_repo, section_name)

    logger.info("Template check completed successfully")


if __name__ == "__main__":
    asyncio.run(check_templates())
