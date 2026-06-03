"""
Selectively restore data from mongodb_backup/rbt BSON dumps into Atlas.

For a single user (default: mujakayadan@outlook.com):
- Merges profile extras (life_story, preferences, llm_usage, etc.) without
  overwriting personal_information from the HTML restore.
- Does NOT touch portfolio (keep HTML-restored portfolio).
- Replaces resumes for that user only (from backup).

Usage:
  uv run python scripts/restore_from_mongodb_backup.py --dry-run
  uv run python scripts/restore_from_mongodb_backup.py
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

from bson import decode_file_iter
from dotenv import dotenv_values
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import OperationFailure

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BACKUP_DIR = ROOT / "mongodb_backup" / "rbt"
DEFAULT_EMAIL = "mujakayadan@outlook.com"

PROFILE_MERGE_FIELDS = (
    "life_story",
    "prompt_preferences",
    "system_preferences",
    "llm_usage",
    "signature_key",
    "api_keys",
)


def load_bson_collection(name: str, backup_dir: Path) -> list[dict[str, Any]]:
    path = backup_dir / f"{name}.bson"
    if not path.is_file():
        return []
    with path.open("rb") as f:
        return list(decode_file_iter(f))


def sanitize_resume(doc: dict[str, Any]) -> dict[str, Any]:
    """Align resume doc with Atlas JSON schema expectations."""
    out = copy.deepcopy(doc)
    for key in (
        "company_name",
        "job_title",
        "job_description",
        "title",
        "template_id",
        "resume_pdf_key",
    ):
        if key in out and out[key] is None:
            out[key] = "" if key != "title" else "Recovered resume"
    if not out.get("title"):
        out["title"] = "Recovered resume"
    if not out.get("template_id"):
        out["template_id"] = "default"
    if not out.get("job_description"):
        out["job_description"] = ""
    out["content"] = out.get("content") or {}
    if not isinstance(out.get("custom_sections"), list):
        out["custom_sections"] = []
    llm = out.get("llm_settings") or {}
    if isinstance(llm, dict):
        out["llm_settings"] = {k: v for k, v in llm.items() if v is not None}
    for link in ("user", "profile", "portfolio"):
        out.pop(link, None)
    return out


def sanitize_profile_merge(
    backup: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Build $set payload for profile fields to merge from backup."""
    updates: dict[str, Any] = {}
    for field in PROFILE_MERGE_FIELDS:
        value = backup.get(field)
        if value is None:
            continue
        if field == "api_keys" and not value:
            continue
        updates[field] = value

    backup_pic = backup.get("profile_picture_key")
    if backup_pic and not current.get("profile_picture_key"):
        updates["profile_picture_key"] = backup_pic

    return updates


def find_user_id(users: list[dict[str, Any]], email: str) -> Any:
    key = email.strip().lower()
    for u in users:
        if (u.get("email") or "").strip().lower() == key:
            return u["_id"]
    return None


def restore(
    *,
    email: str,
    backup_dir: Path,
    target_uri: str,
    db_name: str,
    dry_run: bool,
) -> None:
    users = load_bson_collection("users", backup_dir)
    profiles = load_bson_collection("profiles", backup_dir)
    resumes = load_bson_collection("resumes", backup_dir)
    user_id = find_user_id(users, email)
    if user_id is None:
        raise SystemExit(f"No user in backup for email: {email}")

    backup_profile = next((p for p in profiles if p.get("user_id") == user_id), None)
    if backup_profile is None:
        raise SystemExit(f"No profile in backup for user_id={user_id}")

    backup_resumes = [r for r in resumes if r.get("user_id") == user_id]
    sanitized_resumes = [sanitize_resume(r) for r in backup_resumes]

    print(f"Backup dir: {backup_dir}")
    print(f"Target: {db_name} (dry_run={dry_run})")
    print(f"User {user_id} ({email})")
    print(f"  profile _id: {backup_profile['_id']}")
    print(f"  resumes to restore: {len(sanitized_resumes)}")

    if dry_run:
        merge_preview = sanitize_profile_merge(backup_profile, {})
        print(f"  profile fields to merge: {list(merge_preview.keys())}")
        if backup_profile.get("life_story"):
            print(f"  life_story length: {len(backup_profile['life_story'])} chars")
        return

    client: MongoClient[Any] = MongoClient(target_uri, serverSelectionTimeoutMS=60000)
    try:
        client.admin.command("ping")
        db: Database = client[db_name]

        atlas_user = db.users.find_one({"_id": user_id})
        if not atlas_user:
            raise SystemExit(
                f"User {user_id} not found on target DB — aborting to avoid wrong-account restore."
            )

        atlas_profile = db.profiles.find_one({"_id": backup_profile["_id"]})
        if not atlas_profile:
            raise SystemExit(
                f"Profile {backup_profile['_id']} not found on target — create user/profile first."
            )

        merge_updates = sanitize_profile_merge(backup_profile, atlas_profile)
        if merge_updates:
            db.profiles.update_one(
                {"_id": backup_profile["_id"]},
                {"$set": merge_updates},
            )
            print(f"Merged profile fields: {list(merge_updates.keys())}")
        else:
            print("No profile fields to merge.")

        deleted = db.resumes.delete_many({"user_id": user_id}).deleted_count
        print(f"Removed {deleted} existing resume(s) for user on target.")

        resume_ok = resume_fail = 0
        for doc in sanitized_resumes:
            try:
                db.resumes.replace_one({"_id": doc["_id"]}, doc, upsert=True)
                resume_ok += 1
            except OperationFailure as exc:
                resume_fail += 1
                if resume_fail <= 3:
                    print(f"  resume fail {doc.get('_id')}: {exc.details or exc}")

        print(f"Resumes: {resume_ok} ok, {resume_fail} failed")

        total = db.resumes.count_documents({"user_id": user_id})
        print(f"Done. Resumes for user on target: {total}")
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--backup-dir", type=Path, default=BACKUP_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.backup_dir.is_dir():
        raise SystemExit(f"Backup directory not found: {args.backup_dir}")

    cfg = dotenv_values(ROOT / ".env.local")
    target_uri = cfg.get("MONGODB_URI")
    db_name: str = cfg.get("MONGODB_DATABASE") or "rbt"
    if not target_uri and not args.dry_run:
        raise SystemExit("MONGODB_URI missing in .env.local")

    restore(
        email=args.email,
        backup_dir=args.backup_dir,
        target_uri=target_uri or "",
        db_name=db_name,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
