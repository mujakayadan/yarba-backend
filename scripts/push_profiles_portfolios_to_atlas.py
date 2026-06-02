"""Push profiles and portfolios from local rbt to Atlas (no resumes)."""

from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import OperationFailure

ROOT = Path(__file__).resolve().parents[1]
cfg = dotenv_values(ROOT / ".env.local")
ATLAS = cfg["MONGODB_URI"]
DB: str = cfg.get("MONGODB_DATABASE") or "rbt"

local: MongoClient[Any] = MongoClient("mongodb://localhost:27017")
remote: MongoClient[Any] = MongoClient(ATLAS, serverSelectionTimeoutMS=60000)
ldb: Database = local[DB]
rdb: Database = remote[DB]


def is_structured_portfolio(doc: dict) -> bool:
    """Skip portfolios that store LaTeX strings instead of structured sections."""
    for field in ("career_summary", "skills", "work_experience"):
        value = doc.get(field)
        if isinstance(value, str) and value.strip().startswith("\\"):
            return False
    return True


def sanitize_profile(doc: dict) -> dict:
    out = deepcopy(doc)
    out.pop("user", None)
    out.pop("signature", None)
    out.pop("SUPPORTED_API_KEYS", None)
    out.pop("api_keys", None)
    out.pop("supported_api_keys", None)
    out.pop("preferences", None)
    # Legacy Atlas validator may expect top-level full_name/email
    pi = out.get("personal_information") or {}
    if isinstance(pi, dict):
        if pi.get("full_name"):
            out["full_name"] = pi["full_name"]
        if pi.get("email"):
            out["email"] = pi["email"]
    return out


def sanitize_portfolio(doc: dict) -> dict:
    out = deepcopy(doc)
    out.pop("user", None)
    out.pop("profile", None)
    if not isinstance(out.get("custom_sections"), dict):
        out["custom_sections"] = {"enabled": [], "order": []}
    projects = out.get("projects") or []
    if isinstance(projects, list):
        out["projects"] = [p for p in projects if isinstance(p, dict)]
    return out


# Users: patch hashed_password only (keep Atlas firebase UIDs if present)
for u in ldb.users.find():
    doc = dict(u)
    doc.setdefault("hashed_password", "RECOVERED_FIREBASE_ONLY")
    rdb.users.replace_one({"email": doc["email"]}, doc, upsert=True)

rdb.profiles.delete_many({})
rdb.portfolios.delete_many({})

p_ok = p_fail = 0
for p in ldb.profiles.find():
    try:
        rdb.profiles.insert_one(sanitize_profile(p))
        p_ok += 1
    except OperationFailure as e:
        p_fail += 1
        err_details = e.details or {}
        print("profile fail:", p.get("_id"), err_details.get("errInfo", e))

pf_ok = pf_fail = 0
for p in ldb.portfolios.find():
    if not is_structured_portfolio(p):
        print("skip corrupt portfolio:", p.get("_id"))
        pf_fail += 1
        continue
    try:
        rdb.portfolios.insert_one(sanitize_portfolio(p))
        pf_ok += 1
    except OperationFailure as e:
        pf_fail += 1
        err_details = e.details or {}
        print("portfolio fail:", p.get("_id"), err_details.get("errInfo", e))

# Fill missing portfolio for primary user from user_information if needed
if "user_information" in local.list_database_names():
    ui = local["user_information"]
    for user in rdb.users.find():
        if rdb.portfolios.find_one({"user_id": user["_id"]}):
            continue
        profile = rdb.profiles.find_one({"user_id": user["_id"]})
        if not profile:
            continue
        email = (user.get("email") or "").lower()
        src = None
        for cand in ui.portfolios.find():
            if str(cand.get("user_id", "")).lower() in {
                email.split("@")[0],
                "mujakayadan",
                str(user["_id"]),
            }:
                if is_structured_portfolio(cand):
                    src = cand
                    break
        if src is None:
            src = ui.portfolios.find_one()
        if src and is_structured_portfolio(src):
            from bson import ObjectId

            doc = sanitize_portfolio(src)
            doc["_id"] = ObjectId()
            doc["user_id"] = user["_id"]
            doc["profile_id"] = profile["_id"]
            try:
                rdb.portfolios.insert_one(doc)
                pf_ok += 1
                print(f"filled missing portfolio for {email}")
            except OperationFailure as e:
                err_details = e.details or {}
                print(f"fill portfolio fail {email}:", err_details.get("errInfo", e))

print(
    f"Atlas: users={rdb.users.count_documents({})}, profiles={rdb.profiles.count_documents({})}, portfolios={rdb.portfolios.count_documents({})}, resumes={rdb.resumes.count_documents({})}"
)
print(f"Inserted profiles {p_ok}/{p_ok + p_fail}, portfolios {pf_ok}/{pf_ok + pf_fail}")
local.close()
remote.close()
