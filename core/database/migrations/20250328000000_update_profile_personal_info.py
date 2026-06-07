"""Migration to update profile model with new personal_information structure."""

from datetime import UTC, datetime

from pydantic import ValidationError

from config.logging_config import get_logger
from core.database.migrations.migration_manager import Migration
from core.models.profile import PersonalInformation

logger = get_logger(__name__)


class UpdateProfilePersonalInfoMigration(Migration):
    """Move profile contact fields into personal_information."""

    def upgrade(self) -> None:
        profiles_collection = self.db.profiles
        profiles = list(profiles_collection.find({}))
        logger.info("Starting migration: Update profile personal_information")
        logger.info("Found %s profiles to update", len(profiles))

        success_count = 0
        error_count = 0

        for profile in profiles:
            try:
                if "personal_information" in profile:
                    continue

                personal_information = {
                    "full_name": profile.get("full_name", ""),
                    "email": profile.get("email", ""),
                    "phone": profile.get("phone"),
                    "address": profile.get("address"),
                    "linkedin": profile.get("linkedin"),
                    "github": profile.get("github"),
                    "website": profile.get("website"),
                }
                personal_information = {
                    key: value
                    for key, value in personal_information.items()
                    if value is not None
                }

                try:
                    PersonalInformation(**personal_information)
                except ValidationError as exc:
                    logger.error(
                        "Validation error for profile %s: %s", profile["_id"], exc
                    )
                    error_count += 1
                    continue

                update_result = profiles_collection.update_one(
                    {"_id": profile["_id"]},
                    {
                        "$set": {
                            "personal_information": personal_information,
                            "updated_at": datetime.now(UTC),
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
                else:
                    error_count += 1
            except Exception as exc:
                logger.error("Error processing profile %s: %s", profile.get("_id"), exc)
                error_count += 1

        logger.info(
            "Migration completed: %s profiles updated, %s errors",
            success_count,
            error_count,
        )
        if error_count:
            raise RuntimeError(
                f"Profile personal_information migration failed for {error_count} profile(s)"
            )

    def downgrade(self) -> None:
        profiles_collection = self.db.profiles
        profiles = list(
            profiles_collection.find({"personal_information": {"$exists": True}})
        )
        logger.info(
            "Rolling back profile personal_information for %s profiles", len(profiles)
        )

        for profile in profiles:
            personal_information = profile.get("personal_information", {})
            if not personal_information:
                continue

            update_fields = {
                "full_name": personal_information.get("full_name", ""),
                "email": personal_information.get("email", ""),
                "updated_at": datetime.now(UTC),
            }
            for field in ("phone", "address", "linkedin", "github", "website"):
                if field in personal_information:
                    update_fields[field] = personal_information[field]

            profiles_collection.update_one(
                {"_id": profile["_id"]},
                {"$set": update_fields, "$unset": {"personal_information": ""}},
            )
