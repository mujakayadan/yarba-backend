from pathlib import Path

from dotenv import dotenv_values
from pymongo import MongoClient

cfg = dotenv_values(Path(__file__).resolve().parents[1] / ".env.local")
db = MongoClient(cfg["MONGODB_URI"])[cfg.get("MONGODB_DATABASE", "rbt")]

for u in db.users.find({}, {"email": 1}):
    uid = u["_id"]
    has_p = bool(db.profiles.find_one({"user_id": uid}))
    has_pf = bool(db.portfolios.find_one({"user_id": uid}))
    print(f"{u['email']}: profile={has_p} portfolio={has_pf}")

print(f"resumes: {db.resumes.count_documents({})}")
