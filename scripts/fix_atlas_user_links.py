"""Align Atlas resumes/profiles/portfolios to canonical user_id by email."""

from pathlib import Path

from dotenv import dotenv_values
from pymongo import MongoClient

cfg = dotenv_values(Path(__file__).resolve().parents[1] / ".env.local")
db = MongoClient(cfg["MONGODB_URI"], serverSelectionTimeoutMS=60000)[
    cfg.get("MONGODB_DATABASE", "rbt")
]

for user in db.users.find():
    email = (user.get("email") or "").lower()
    if not email:
        continue
    uid = user["_id"]
    profile = db.profiles.find_one({"user_id": uid})
    if not profile:
        profile = db.profiles.find_one(
            {"personal_information.email": {"$regex": f"^{email}$", "$options": "i"}}
        )
        if profile:
            db.profiles.update_one({"_id": profile["_id"]}, {"$set": {"user_id": uid}})

    portfolio = db.portfolios.find_one({"user_id": uid})
    if not portfolio and profile:
        from datetime import UTC, datetime

        from bson import ObjectId

        db.portfolios.insert_one(
            {
                "_id": ObjectId(),
                "user_id": uid,
                "profile_id": profile["_id"],
                "career_summary": {},
                "skills": [],
                "work_experience": [],
                "education": [],
                "projects": [],
                "awards": [],
                "publications": [],
                "certifications": [],
                "custom_sections": {"enabled": [], "order": []},
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        portfolio = db.portfolios.find_one({"user_id": uid})

    if not profile or not portfolio:
        print(f"skip {email}: missing profile or portfolio")
        continue

    pid, pfid, poid = uid, profile["_id"], portfolio["_id"]
    n = 0
    for resume in db.resumes.find():
        pi = (resume.get("content") or {}).get("personal_information") or {}
        r_email = (pi.get("email") or "").lower() if isinstance(pi, dict) else ""
        legacy = str(resume.get("user_id", "")).lower() in {
            "mujakayadan",
            "test_user",
            str(uid),
        }
        if r_email == email or legacy:
            db.resumes.update_one(
                {"_id": resume["_id"]},
                {
                    "$set": {
                        "user_id": pid,
                        "profile_id": pfid,
                        "portfolio_id": poid,
                    }
                },
            )
            n += 1
    print(f"{email}: linked {n} resumes")

print("Done.")
