#!/usr/bin/env python
"""Migration script for user preferences.

This script migrates user preferences from the legacy structure to the new structure.
- Migrates from the preferences.X_details structure to prompt_preferences.X structure
- Migrates from legacy feature_preferences to system_preferences.features
- Migrates from llm_preferences to system_preferences.llm
- Migrates from default_latex_templates to system_preferences.templates

This is a one-time migration script. After running, the legacy preferences will still
be available but all new code will use the new structure.
"""

# Load environment variables from .env.local and .env files
import os
from pathlib import Path

from dotenv import load_dotenv

# First try .env.local (higher priority)
env_local = Path(".env.local")
if env_local.exists():
    print(f"Loading environment from {env_local.absolute()}")
    load_dotenv(dotenv_path=env_local)
else:
    print("No .env.local file found")

# Then try .env (lower priority)
env_file = Path(".env")
if env_file.exists():
    print(f"Loading environment from {env_file.absolute()}")
    load_dotenv(dotenv_path=env_file)
else:
    print("No .env file found")

# Print loaded MongoDB URI for debugging (masked for security)
mongodb_uri = os.environ.get("MONGODB_URI", "")
if mongodb_uri:
    # Mask sensitive parts for logging
    parts = mongodb_uri.split("://")
    if len(parts) > 1:
        protocol = parts[0]
        rest = parts[1]
        if "@" in rest:
            # Handle username:password@host format
            auth_host = rest.split("@")
            masked_uri = f"{protocol}://****:****@{auth_host[1]}"
        else:
            # No auth in the URI
            masked_uri = mongodb_uri
        print(f"Loaded MongoDB URI: {masked_uri}")
    else:
        print("MongoDB URI loaded but format is not as expected")
else:
    print("No MongoDB URI found in environment variables")

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger
from core.database.init import init_db
from core.models.profile import PromptPreferences, SystemPreferences
from core.repositories.profile_repository import ProfileRepository

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def get_all_profiles():
    """Get all profiles from the database."""
    profile_repo = ProfileRepository()
    return await profile_repo.get_all()


async def migrate_profile_preferences(profile_id, dry_run=True, remove_legacy=False):
    """
    Migrate preferences for a single profile.

    Args:
        profile_id: The ID of the profile to migrate
        dry_run: If True, just simulate the migration without saving
        remove_legacy: If True, remove legacy preferences after migration

    Returns:
        bool: True if migration was successful, False otherwise
    """
    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_id(profile_id)

    if not profile:
        logger.error(f"Profile with ID {profile_id} not found")
        return False

    if not hasattr(profile, "preferences"):
        logger.warning(f"Profile {profile_id} has no preferences to migrate")
        return True

    # Initialize the new preferences if they don't exist
    if not hasattr(profile, "prompt_preferences") or profile.prompt_preferences is None:
        profile.prompt_preferences = PromptPreferences()

    if not hasattr(profile, "system_preferences") or profile.system_preferences is None:
        profile.system_preferences = SystemPreferences()

    # Migrate project preferences
    if hasattr(profile.preferences, "project_details"):
        profile.prompt_preferences.project = profile.preferences.project_details
        logger.info("Migrated project_details to prompt_preferences.project")

    # Migrate work experience preferences
    if hasattr(profile.preferences, "work_experience_details"):
        profile.prompt_preferences.work_experience = (
            profile.preferences.work_experience_details
        )
        logger.info(
            "Migrated work_experience_details to prompt_preferences.work_experience"
        )

    # Migrate skills preferences
    if hasattr(profile.preferences, "skills_details"):
        profile.prompt_preferences.skills = profile.preferences.skills_details
        logger.info("Migrated skills_details to prompt_preferences.skills")

    # Migrate career summary preferences
    if hasattr(profile.preferences, "career_summary_details"):
        profile.prompt_preferences.career_summary = (
            profile.preferences.career_summary_details
        )
        logger.info(
            "Migrated career_summary_details to prompt_preferences.career_summary"
        )

    # Migrate education preferences
    if hasattr(profile.preferences, "education_details"):
        profile.prompt_preferences.education = profile.preferences.education_details
        logger.info("Migrated education_details to prompt_preferences.education")

    # Migrate cover letter preferences
    if hasattr(profile.preferences, "cover_letter_details"):
        profile.prompt_preferences.cover_letter = (
            profile.preferences.cover_letter_details
        )
        logger.info("Migrated cover_letter_details to prompt_preferences.cover_letter")

    # Migrate awards preferences
    if hasattr(profile.preferences, "awards_details"):
        profile.prompt_preferences.awards = profile.preferences.awards_details
        logger.info("Migrated awards_details to prompt_preferences.awards")

    # Migrate publications preferences
    if hasattr(profile.preferences, "publications_details"):
        profile.prompt_preferences.publications = (
            profile.preferences.publications_details
        )
        logger.info("Migrated publications_details to prompt_preferences.publications")

    # Migrate system preferences
    if hasattr(profile.preferences, "feature_preferences"):
        profile.system_preferences.features = profile.preferences.feature_preferences
        logger.info("Migrated feature_preferences to system_preferences.features")

    if hasattr(profile.preferences, "llm_preferences"):
        profile.system_preferences.llm = profile.preferences.llm_preferences
        logger.info("Migrated llm_preferences to system_preferences.llm")

    if hasattr(profile.preferences, "default_latex_templates"):
        profile.system_preferences.templates = (
            profile.preferences.default_latex_templates
        )
        logger.info("Migrated default_latex_templates to system_preferences.templates")

    if not dry_run:
        try:
            # Remove legacy preferences if requested
            if remove_legacy:
                # Use the MongoDB $unset operator to remove the preferences field
                from beanie.odm.operators.update.general import Unset

                await profile.update({"$unset": {"preferences": ""}})
                logger.info(f"Removed legacy preferences from profile {profile_id}")
            else:
                # Save directly with Beanie's save method
                await profile.save()
            return True
        except Exception as e:
            logger.error(f"Error saving migrated profile {profile_id}: {str(e)}")
            return False
    return True


async def migrate_all_preferences(dry_run=True, remove_legacy=False):
    """
    Migrate preferences for all profiles.

    Args:
        dry_run: If True, just simulate the migration without saving
        remove_legacy: If True, remove legacy preferences after migration

    Returns:
        Tuple[int, int]: Count of (successful, failed) migrations
    """
    profiles = await get_all_profiles()

    success_count = 0
    fail_count = 0

    logger.info(
        f"Starting migration of {len(profiles)} profiles (dry_run={dry_run}, remove_legacy={remove_legacy})"
    )

    for profile in profiles:
        result = await migrate_profile_preferences(
            profile.id, dry_run=dry_run, remove_legacy=remove_legacy
        )
        if result:
            success_count += 1
        else:
            fail_count += 1

    logger.info(f"Migration complete: {success_count} succeeded, {fail_count} failed")
    return success_count, fail_count


async def main():
    """Run the migration."""
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate user preferences to new format"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate migration without saving"
    )
    parser.add_argument("--profile-id", help="Migrate only the specified profile ID")
    parser.add_argument(
        "--remove-legacy",
        action="store_true",
        help="Remove legacy preferences after migration",
    )
    parser.add_argument(
        "--mongodb-uri",
        help="Override MongoDB URI (instead of using environment variables)",
    )
    args = parser.parse_args()

    # Override MongoDB URI if provided
    if args.mongodb_uri:
        os.environ["MONGODB_URI"] = args.mongodb_uri
        print(
            f"Using provided MongoDB URI: {args.mongodb_uri.split('@')[-1] if '@' in args.mongodb_uri else '(no auth part)'}"
        )

    # Initialize database
    await init_db()

    if args.profile_id:
        # Migrate single profile
        logger.info(
            f"Migrating preferences for profile ID: {args.profile_id} (remove_legacy={args.remove_legacy})"
        )
        result = await migrate_profile_preferences(
            args.profile_id, dry_run=args.dry_run, remove_legacy=args.remove_legacy
        )
        if result:
            logger.info("Migration successful")
            return 0
        else:
            logger.error("Migration failed")
            return 1
    else:
        # Migrate all profiles
        success, fail = await migrate_all_preferences(
            dry_run=args.dry_run, remove_legacy=args.remove_legacy
        )

        if fail > 0:
            logger.warning(
                f"Some migrations failed: {fail} failed, {success} succeeded"
            )
            return 1
        else:
            logger.info(f"All migrations successful: {success} profiles migrated")
            return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
