"""Migration to update profile model with new personal_information structure."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from beanie import PydanticObjectId
from pydantic import ValidationError
from pymongo.errors import PyMongoError

from config.logging_config import get_logger
from core.database.migrations.migration_manager import MigrationBase
from core.models.profile import PersonalInformation, Profile
from core.repositories.profile_repository import ProfileRepository

logger = get_logger(__name__)


class UpdateProfilePersonalInfoMigration(MigrationBase):
    """Migration to update profile model with personal_information structure."""

    name = "update_profile_personal_info"
    version = "20250328000000"
    description = "Updates the profile model to use personal_information structure"

    async def up(self) -> bool:
        """Execute the migration up (forward).

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get MongoDB client and collection
            client = self.get_client()
            db = client.get_database(self.db_name)
            profiles_collection = db.get_collection("profiles")

            logger.info("Starting migration: Update profile personal_information")

            # Find all profiles
            profiles = await profiles_collection.find({}).to_list(length=None)
            logger.info(f"Found {len(profiles)} profiles to update")

            success_count = 0
            error_count = 0

            # Process each profile
            for profile in profiles:
                try:
                    # Extract personal information fields
                    personal_information = {
                        "full_name": profile.get("full_name", ""),
                        "email": profile.get("email", ""),
                        "phone": profile.get("phone"),
                        "address": profile.get("address"),
                        "linkedin": profile.get("linkedin"),
                        "github": profile.get("github"),
                        "website": profile.get("website"),
                    }

                    # Remove None values (they'll be None by default in the model)
                    personal_information = {
                        k: v for k, v in personal_information.items() if v is not None
                    }

                    # Check if personal_information already exists
                    if "personal_information" in profile:
                        logger.debug(
                            f"Profile {profile['_id']} already has personal_information"
                        )
                        continue

                    # Validate fields with the model
                    try:
                        # Create PersonalInformation object to validate
                        PersonalInformation(**personal_information)
                    except ValidationError as ve:
                        logger.error(
                            f"Validation error for profile {profile['_id']}: {ve}"
                        )
                        error_count += 1
                        continue

                    # Update profile with new personal_information field and remove old fields
                    update_result = await profiles_collection.update_one(
                        {"_id": profile["_id"]},
                        {
                            "$set": {
                                "personal_information": personal_information,
                                "updated_at": datetime.now(timezone.utc),
                            },
                            "$unset": {
                                "full_name": "",
                                "email": "",
                                "phone": "",
                                "address": "",
                                "linkedin": "",
                                "github": "",
                                "website": "",
                            },
                        },
                    )

                    if update_result.modified_count > 0:
                        success_count += 1
                        logger.debug(
                            f"Updated profile {profile['_id']} with personal_information"
                        )
                    else:
                        logger.warning(f"Failed to update profile {profile['_id']}")
                        error_count += 1

                except Exception as e:
                    logger.error(f"Error processing profile {profile.get('_id')}: {e}")
                    error_count += 1

            logger.info(
                f"Migration completed: {success_count} profiles updated, {error_count} errors"
            )
            return error_count == 0

        except PyMongoError as e:
            logger.error(f"MongoDB error during migration: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during migration: {e}")
            return False

    async def down(self) -> bool:
        """Execute the migration down (rollback).

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get MongoDB client and collection
            client = self.get_client()
            db = client.get_database(self.db_name)
            profiles_collection = db.get_collection("profiles")

            logger.info("Starting rollback: Update profile personal_information")

            # Find all profiles with personal_information field
            profiles = await profiles_collection.find(
                {"personal_information": {"$exists": True}}
            ).to_list(length=None)

            logger.info(f"Found {len(profiles)} profiles to rollback")

            success_count = 0
            error_count = 0

            # Process each profile
            for profile in profiles:
                try:
                    # Extract personal information fields
                    personal_information = profile.get("personal_information", {})

                    if not personal_information:
                        logger.warning(
                            f"Profile {profile['_id']} has empty personal_information"
                        )
                        continue

                    # Update profile by moving fields back to root level
                    update_fields = {
                        "full_name": personal_information.get("full_name", ""),
                        "email": personal_information.get("email", ""),
                        "updated_at": datetime.now(timezone.utc),
                    }

                    # Add optional fields if they exist
                    for field in ["phone", "address", "linkedin", "github", "website"]:
                        if field in personal_information:
                            update_fields[field] = personal_information[field]

                    # Update the document
                    update_result = await profiles_collection.update_one(
                        {"_id": profile["_id"]},
                        {
                            "$set": update_fields,
                            "$unset": {"personal_information": ""},
                        },
                    )

                    if update_result.modified_count > 0:
                        success_count += 1
                        logger.debug(f"Rolled back profile {profile['_id']}")
                    else:
                        logger.warning(f"Failed to rollback profile {profile['_id']}")
                        error_count += 1

                except Exception as e:
                    logger.error(
                        f"Error rolling back profile {profile.get('_id')}: {e}"
                    )
                    error_count += 1

            logger.info(
                f"Rollback completed: {success_count} profiles updated, {error_count} errors"
            )
            return error_count == 0

        except PyMongoError as e:
            logger.error(f"MongoDB error during rollback: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during rollback: {e}")
            return False

    async def validate(self) -> bool:
        """Validate the migration was successful.

        Returns:
            bool: True if validation passes, False otherwise
        """
        try:
            client = self.get_client()
            db = client.get_database(self.db_name)
            profiles_collection = db.get_collection("profiles")

            # Check if any profiles still have the old field structure
            legacy_profiles_count = await profiles_collection.count_documents(
                {"full_name": {"$exists": True}}
            )

            # Check if all profiles have the new structure
            migrated_profiles_count = await profiles_collection.count_documents(
                {"personal_information": {"$exists": True}}
            )

            total_profiles = await profiles_collection.count_documents({})

            logger.info(
                f"Validation: {migrated_profiles_count}/{total_profiles} profiles migrated, "
                f"{legacy_profiles_count} legacy profiles remaining"
            )

            # For validation to pass, all profiles should have personal_information
            # and none should have the old full_name field
            return (
                migrated_profiles_count == total_profiles and legacy_profiles_count == 0
            )

        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return False


# Make the migration available to the migration manager
migrations = [UpdateProfilePersonalInfoMigration]
