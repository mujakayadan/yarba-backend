"""
Create cover_letters collection and migrate existing cover letters

Migration created at: 2024-06-08T00:00:00
"""

from pymongo.database import Database

from core.database.migrations.migration_manager import Migration


class CreateCoverLettersCollectionMigration(Migration):
    """
    Create cover_letters collection and migrate existing cover letters from resumes collection
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        # Create the cover_letters collection
        self.db.create_collection("cover_letters")
        self.db.command(
            {
                "collMod": "cover_letters",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "profile_id"],
                        "properties": {
                            "user_id": {"bsonType": "objectId"},
                            "profile_id": {"bsonType": "objectId"},
                            "portfolio_id": {"bsonType": "objectId"},
                            "resume_id": {"bsonType": "objectId"},
                            "title": {"bsonType": "string"},
                            "version": {"bsonType": "int"},
                            "template_id": {"bsonType": "string"},
                            "company_name": {"bsonType": "string"},
                            "job_title": {"bsonType": "string"},
                            "job_description": {"bsonType": "string"},
                            "content": {"bsonType": "object"},
                            "cover_letter_content": {"bsonType": "string"},
                            "cover_letter_pdf": {"bsonType": "binData"},
                            "llm_settings": {"bsonType": "object"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Create indexes for the cover_letters collection
        self.db.cover_letters.create_index("user_id")
        self.db.cover_letters.create_index("profile_id")
        self.db.cover_letters.create_index("portfolio_id")
        self.db.cover_letters.create_index("resume_id")

        # Migrate existing cover letters from resumes collection to cover_letters collection
        cover_letters = list(self.db.resumes.find({"is_cover_letter": True}))

        if cover_letters:
            for cover_letter in cover_letters:
                # Convert to new schema
                new_cover_letter = {
                    "user_id": cover_letter["user_id"],
                    "profile_id": cover_letter["profile_id"],
                    "portfolio_id": cover_letter.get("portfolio_id"),
                    "resume_id": None,  # No resume link in the old structure
                    "title": cover_letter.get("title", "My Cover Letter"),
                    "version": cover_letter.get("version"),
                    "template_id": cover_letter.get("template_id", "default"),
                    "company_name": cover_letter.get("company_name"),
                    "job_title": cover_letter.get("job_title"),
                    "job_description": cover_letter.get("job_description", ""),
                    "content": cover_letter.get("content", {}),
                    "cover_letter_content": cover_letter.get("cover_letter_content"),
                    "cover_letter_pdf": cover_letter.get("cover_letter_pdf"),
                    "llm_settings": cover_letter.get("llm_settings", {}),
                    "created_at": cover_letter.get("created_at"),
                    "updated_at": cover_letter.get("updated_at"),
                }

                # Insert into cover_letters collection
                self.db.cover_letters.insert_one(new_cover_letter)

                # Delete from resumes collection
                self.db.resumes.delete_one({"_id": cover_letter["_id"]})

    def downgrade(self) -> None:
        """Revert the migration."""
        # Migrate cover letters back to resumes
        cover_letters = list(self.db.cover_letters.find())

        if cover_letters:
            for cover_letter in cover_letters:
                # Convert to old schema
                resume_doc = {
                    "user_id": cover_letter["user_id"],
                    "profile_id": cover_letter["profile_id"],
                    "portfolio_id": cover_letter.get("portfolio_id"),
                    "title": cover_letter.get("title", "My Cover Letter"),
                    "version": cover_letter.get("version"),
                    "template_id": cover_letter.get("template_id", "default"),
                    "company_name": cover_letter.get("company_name"),
                    "job_title": cover_letter.get("job_title"),
                    "job_description": cover_letter.get("job_description", ""),
                    "is_cover_letter": True,  # Set flag
                    "content": cover_letter.get("content", {}),
                    "cover_letter_content": cover_letter.get("cover_letter_content"),
                    "cover_letter_pdf": cover_letter.get("cover_letter_pdf"),
                    "llm_settings": cover_letter.get("llm_settings", {}),
                    "created_at": cover_letter.get("created_at"),
                    "updated_at": cover_letter.get("updated_at"),
                    "custom_sections": [],
                    "resume_pdf": None,
                }

                # Insert into resumes collection
                self.db.resumes.insert_one(resume_doc)

        # Drop the cover_letters collection
        self.db.cover_letters.drop()
