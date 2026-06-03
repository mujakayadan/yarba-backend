"""Copy local mongodb://localhost:27017/rbt to Atlas using .env.local MONGODB_URI."""

import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pymongo import MongoClient
from pymongo.database import Database

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "mongodb_backup"
LEGACY_PASSWORD = "RECOVERED_FIREBASE_ONLY"


def main() -> None:
    cfg = dotenv_values(ROOT / ".env.local")
    target_uri = cfg.get("MONGODB_URI")
    db_name: str = cfg.get("MONGODB_DATABASE") or "rbt"
    if not target_uri:
        raise SystemExit("MONGODB_URI missing in .env.local")

    local: MongoClient[Any] = MongoClient(
        "mongodb://localhost:27017", serverSelectionTimeoutMS=5000
    )
    local.admin.command("ping")
    db: Database = local[db_name]

    result = db.users.update_many(
        {"hashed_password": {"$exists": False}},
        {"$set": {"hashed_password": LEGACY_PASSWORD}},
    )
    print(f"Patched {result.modified_count} users with legacy hashed_password field")

    for coll, count in [
        ("users", db.users.count_documents({})),
        ("profiles", db.profiles.count_documents({})),
        ("portfolios", db.portfolios.count_documents({})),
        ("resumes", db.resumes.count_documents({})),
    ]:
        print(f"  local {coll}: {count}")

    BACKUP_DIR.mkdir(exist_ok=True)
    dump_cmd = [
        "mongodump",
        "--uri=mongodb://localhost:27017",
        f"--db={db_name}",
        f"--out={BACKUP_DIR}",
    ]
    print("Running mongodump...")
    subprocess.run(dump_cmd, check=True)

    restore_cmd = [
        "mongorestore",
        f"--uri={target_uri}",
        f"--db={db_name}",
        "--drop",
        str(BACKUP_DIR / db_name),
    ]
    print("Running mongorestore to Atlas...")
    subprocess.run(restore_cmd, check=True)

    remote: MongoClient[Any] = MongoClient(target_uri, serverSelectionTimeoutMS=30000)
    remote.admin.command("ping")
    rdb: Database = remote[db_name]
    print("Atlas counts:")
    for coll in (
        "users",
        "profiles",
        "portfolios",
        "resumes",
    ):
        if coll in rdb.list_collection_names():
            print(f"  {coll}: {rdb[coll].count_documents({})}")

    local.close()
    remote.close()
    print("Restore complete.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
