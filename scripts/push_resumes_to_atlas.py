"""Insert sanitized resumes from local rbt into Atlas (fixes validation failures)."""

from copy import deepcopy
from pathlib import Path

from dotenv import dotenv_values
from pymongo import MongoClient
from pymongo.errors import OperationFailure

ROOT = Path(__file__).resolve().parents[1]
cfg = dotenv_values(ROOT / ".env.local")
ATLAS = cfg["MONGODB_URI"]
DB = cfg.get("MONGODB_DATABASE", "rbt")

local = MongoClient("mongodb://localhost:27017")
remote = MongoClient(ATLAS, serverSelectionTimeoutMS=60000)
ldb, rdb = local[DB], remote[DB]


def _str_or_empty(value) -> str:
    if value is None:
        return ""
    return str(value)


def sanitize_resume(doc: dict) -> dict:
    out = deepcopy(doc)
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
    if not isinstance(out["custom_sections"], list):
        out["custom_sections"] = []
    llm = out.get("llm_settings") or {}
    if isinstance(llm, dict):
        clean_llm = {}
        for k, v in llm.items():
            if v is not None:
                clean_llm[k] = v
        out["llm_settings"] = clean_llm
    out.pop("user", None)
    out.pop("profile", None)
    out.pop("portfolio", None)
    out.pop("_recovery_source", None)
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


# Re-sync portfolios missing on Atlas
rdb.portfolios.delete_many({})
for p in ldb.portfolios.find():
    try:
        rdb.portfolios.insert_one(sanitize_portfolio(p))
    except OperationFailure as e:
        print("portfolio fail:", p.get("_id"), e.details)

rdb.resumes.delete_many({})
ok = 0
fail = 0
for resume in ldb.resumes.find():
    doc = sanitize_resume(resume)
    try:
        rdb.resumes.insert_one(doc)
        ok += 1
    except OperationFailure as e:
        fail += 1
        if fail <= 3:
            print("resume fail:", doc.get("_id"), e.details)

print(
    f"Atlas resumes: {ok} ok, {fail} failed, total now {rdb.resumes.count_documents({})}"
)
local.close()
remote.close()
