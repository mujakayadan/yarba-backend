"""
Fix portfolio user_id type and remove professional_title

Migration created at: 2024-06-23T00:00:00
"""

from bson import ObjectId

from config import logging_config
from core.database.migrations.migration_manager import Migration

logger = logging_config.get_logger(__name__)


class FixPortfolioUserIdMigration(Migration):
    """
    Fix portfolio user_id type to be ObjectId and remove professional_title field.

    This migration:
    1. Converts string user_ids to ObjectId in the portfolios collection
    2. Removes the deprecated professional_title field
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        logger.info("Running fix_portfolio_user_id migration")

        # Step 1: Find all portfolios with string user_ids and convert them
        portfolios_to_update = []

        for portfolio in self.db.portfolios.find({}):
            if (
                "user_id" in portfolio
                and isinstance(portfolio["user_id"], str)
                and not portfolio["user_id"].startswith("ObjectId")
            ):
                logger.warning(
                    f"Found portfolio with string user_id: {portfolio['_id']}, user_id: {portfolio['user_id']}"
                )

                try:
                    # First attempt to convert the string to ObjectId
                    if ObjectId.is_valid(portfolio["user_id"]):
                        # It's a valid ObjectId string, convert directly
                        portfolios_to_update.append(
                            {
                                "portfolio_id": portfolio["_id"],
                                "user_id": ObjectId(portfolio["user_id"]),
                            }
                        )
                        logger.info(
                            f"Will convert string ObjectId for portfolio {portfolio['_id']}"
                        )
                        continue

                    # If not a valid ObjectId, try to find matching profile
                    matching_profile = self.db.profiles.find_one(
                        {"user_id": portfolio["user_id"]}
                    )

                    if matching_profile:
                        # Update portfolio with proper ObjectId
                        portfolios_to_update.append(
                            {
                                "portfolio_id": portfolio["_id"],
                                "user_id": matching_profile["user_id"],
                            }
                        )
                        logger.info(
                            f"Found matching profile for {portfolio['user_id']}"
                        )
                    else:
                        logger.error(
                            f"Could not find matching profile for portfolio {portfolio['_id']}, user_id: {portfolio['user_id']}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error processing portfolio {portfolio['_id']}: {str(e)}"
                    )

        # Update all portfolios with proper ObjectIds
        for update in portfolios_to_update:
            self.db.portfolios.update_one(
                {"_id": update["portfolio_id"]},
                {"$set": {"user_id": update["user_id"]}},
            )
            logger.info(
                f"Updated portfolio {update['portfolio_id']} with ObjectId user_id"
            )

        # Step 2: Remove professional_title field
        self.db.portfolios.update_many({}, {"$unset": {"professional_title": ""}})
        logger.info("Removed professional_title field from all portfolios")

        # Step 3: Update the schema validator to enforce ObjectId type
        self.db.command(
            {
                "collMod": "portfolios",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id"],
                        "properties": {
                            "user_id": {"bsonType": "objectId"},
                            "profile_id": {"bsonType": "objectId"},
                            "career_summary": {"bsonType": "object"},
                            "skills": {"bsonType": "array"},
                            "work_experience": {"bsonType": "array"},
                            "education": {"bsonType": "array"},
                            "projects": {"bsonType": "array"},
                            "awards": {"bsonType": "array"},
                            "publications": {"bsonType": "array"},
                            "certifications": {"bsonType": "array"},
                            "custom_sections": {"bsonType": "object"},
                            "is_active": {"bsonType": "bool"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )
        logger.info("Updated portfolios schema to enforce ObjectId type for user_id")

    def downgrade(self) -> None:
        """Revert the migration."""
        # This is a data correction migration, so downgrade would be complex
        # and potentially destructive. It's best left as a manual process if needed.
        logger.warning("Downgrade not implemented for fix_portfolio_user_id migration")
