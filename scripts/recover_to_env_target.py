"""Run local merge recovery and write to MONGODB_URI from .env.local."""

from pathlib import Path

from dotenv import dotenv_values

from recover_local_mongodb import recover

cfg = dotenv_values(Path(__file__).resolve().parents[1] / ".env.local")
uri = cfg.get("MONGODB_URI")
db_name = cfg.get("MONGODB_DATABASE", "rbt")
if not uri:
    raise SystemExit("MONGODB_URI missing in .env.local")

# Merge from user_information only — local rbt is already the merged snapshot.
SOURCE_DBS = ("user_information",)

print(f"Target database: {db_name}")
print(f"Sources: {SOURCE_DBS}")
import recover_local_mongodb as mod

mod.SOURCE_DBS = SOURCE_DBS
recover("mongodb://localhost:27017", uri, db_name, dry_run=False)
print("Atlas recovery complete.")
