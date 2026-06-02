from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pymongo import MongoClient
from pymongo.database import Database

cfg = dotenv_values(Path(__file__).resolve().parents[1] / ".env.local")
_db_name: str = cfg.get("MONGODB_DATABASE") or "rbt"
_client: MongoClient[Any] = MongoClient(cfg["MONGODB_URI"])
db: Database = _client[_db_name]

for u in db.users.find({}, {"email": 1}):
    uid = u["_id"]
    has_p = bool(db.profiles.find_one({"user_id": uid}))
    has_pf = bool(db.portfolios.find_one({"user_id": uid}))
    print(f"{u['email']}: profile={has_p} portfolio={has_pf}")

print(f"resumes: {db.resumes.count_documents({})}")
