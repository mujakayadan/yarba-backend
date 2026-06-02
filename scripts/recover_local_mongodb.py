"""
Merge local MongoDB databases (rbt + user_information) into current app schema.

Maximum-coverage recovery:
- Users/profiles/portfolios: merge by email/user_id, keep richest document
- Resumes: import current-schema docs as-is; convert legacy embedded resumes to content dict
- LaTeX seeds: merge preambles/tex_headers from both sources
- portfolio_items: fold project-like items into portfolio.projects when missing

Default target: mongodb://localhost:27017/rbt (use --target-uri for Atlas).

Usage:
  uv run python scripts/recover_local_mongodb.py --dry-run
  uv run python scripts/recover_local_mongodb.py
  uv run python scripts/recover_local_mongodb.py --target-uri "$MONGODB_URI"
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

SOURCE_DBS = ("rbt", "user_information")
DEFAULT_TARGET_URI = "mongodb://localhost:27017"
DEFAULT_TARGET_DB = "rbt"

RESUME_CONTENT_KEYS = (
    "personal_information",
    "career_summary",
    "skills",
    "work_experience",
    "education",
    "projects",
    "publications",
    "awards",
)

# Placeholder satisfies legacy MongoDB JSON Schema on Atlas; auth is Firebase-only.
LEGACY_PASSWORD_PLACEHOLDER = "RECOVERED_FIREBASE_ONLY"

USER_STRIP_FIELDS = {
    "hashed_password",
    "login_attempts",
    "account_locked_until",
    "reset_password_token",
    "reset_password_expires",
    "verification_token",
    "preferences",
    "full_name",
    "is_verified",
    "user",
}

PROFILE_STRIP_FIELDS = {
    "user",
    "signature",
    "SUPPORTED_API_KEYS",
    "api_keys",
    "supported_api_keys",
    "preferences",
}


def _oid(value: Any) -> ObjectId | None:
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _email_key(email: str | None) -> str | None:
    return email.strip().lower() if email else None


def _unique_username(email: str, taken: set[str]) -> str:
    local, _, domain = email.partition("@")
    base = local.lower().replace(".", "_") or "user"
    if domain:
        domain_tag = domain.split(".")[0]
        if domain_tag not in base:
            base = f"{base}_{domain_tag}"
    candidate = base[:50]
    counter = 1
    while candidate in taken:
        candidate = f"{base[:40]}_{counter}"
        counter += 1
    taken.add(candidate)
    return candidate


def _content_fingerprint(doc: dict[str, Any]) -> str:
    payload = json.dumps(doc, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def legacy_resume_to_content(doc: dict[str, Any]) -> dict[str, Any]:
    """Map embedded legacy resume sections into Resume.content."""
    content: dict[str, Any] = {}
    for key in RESUME_CONTENT_KEYS:
        if key in doc and doc[key] not in (None, [], {}):
            content[key] = copy.deepcopy(doc[key])
    if not content.get("career_summary") and doc.get("title"):
        content["career_summary"] = {
            "job_title": doc.get("job_title") or doc.get("title") or "Professional",
            "default_summary": "",
        }
    return content


def normalize_user(doc: dict[str, Any]) -> dict[str, Any] | None:
    email = doc.get("email")
    if not email:
        return None
    out = {k: v for k, v in doc.items() if k not in USER_STRIP_FIELDS}
    out["email"] = email
    if not out.get("username"):
        out["username"] = _email_key(email).split("@")[0] if email else "user"
    email_key = _email_key(email)
    if email_key and email_key in KNOWN_FIREBASE_BY_EMAIL:
        out["firebase_uid"] = KNOWN_FIREBASE_BY_EMAIL[email_key]
        out["auth_provider"] = "firebase.password"
    uid = out.get("firebase_uid")
    if not uid:
        out["firebase_uid"] = f"recovered-local-{out['_id']}"
        out["auth_provider"] = out.get("auth_provider") or "firebase.password"
    if out.get("auth_provider") == "local":
        out["auth_provider"] = "firebase.password"
    out.setdefault("is_new_user", False)
    out.setdefault("current_setup_step", 99)
    out.setdefault("is_active", True)
    out.setdefault("is_superuser", False)
    out.setdefault("email_verified", bool(doc.get("email_verified", False)))
    out.setdefault("subscription_status", doc.get("subscription_status") or "free")
    out["hashed_password"] = LEGACY_PASSWORD_PLACEHOLDER
    out["created_at"] = _dt(out.get("created_at"))
    out["updated_at"] = _dt(out.get("updated_at"))
    return out


def migrate_profile_preferences(doc: dict[str, Any]) -> dict[str, Any]:
    """Fold legacy preferences into prompt_preferences / system_preferences."""
    out = {k: v for k, v in doc.items() if k not in PROFILE_STRIP_FIELDS}
    prefs = doc.get("preferences") or {}
    if prefs and not out.get("prompt_preferences"):
        prompt = {}
        for section in (
            "project_details",
            "work_experience_details",
            "skills_details",
            "career_summary_details",
            "education_details",
            "cover_letter_details",
            "awards_details",
            "publications_details",
        ):
            if section in prefs:
                key = section.replace("_details", "")
                prompt[key] = prefs[section]
        if prompt:
            out["prompt_preferences"] = prompt
    if prefs and not out.get("system_preferences"):
        system: dict[str, Any] = {}
        if "feature_preferences" in prefs:
            system["features"] = prefs["feature_preferences"]
        if "notifications" in prefs:
            system["notifications"] = prefs["notifications"]
        if "privacy" in prefs:
            system["privacy"] = prefs["privacy"]
        if "llm_preferences" in prefs:
            system["llm"] = prefs["llm_preferences"]
        if "default_latex_templates" in prefs:
            system["templates"] = prefs["default_latex_templates"]
        if system:
            out["system_preferences"] = system
    if doc.get("prompt_preferences"):
        out["prompt_preferences"] = doc["prompt_preferences"]
    if doc.get("system_preferences"):
        out["system_preferences"] = doc["system_preferences"]
    if not out.get("personal_information") and doc.get("email"):
        out["personal_information"] = {
            "full_name": doc.get("full_name") or "",
            "email": doc["email"],
        }
    out["created_at"] = _dt(out.get("created_at"))
    out["updated_at"] = _dt(out.get("updated_at"))
    return out


def normalize_portfolio(
    doc: dict[str, Any], profile_id: ObjectId | None
) -> dict[str, Any]:
    out = copy.deepcopy(doc)
    out.pop("is_active", None)
    out.pop("template_preferences", None)
    out.pop("version", None)
    out.pop("user_reference", None)
    out.pop("user", None)
    out.pop("profile", None)
    uid = _oid(out.get("user_id"))
    if uid:
        out["user_id"] = uid
    if profile_id:
        out["profile_id"] = profile_id
    if not isinstance(out.get("custom_sections"), dict):
        out["custom_sections"] = {"enabled": [], "order": []}
    out["created_at"] = _dt(out.get("created_at"))
    out["updated_at"] = _dt(out.get("updated_at"))
    return out


def portfolio_item_to_project(item: dict[str, Any]) -> dict[str, Any]:
    bullets = item.get("highlights") or item.get("description")
    if isinstance(bullets, str):
        bullet_points = [bullets] if bullets else []
    elif isinstance(bullets, list):
        bullet_points = [str(b) for b in bullets]
    else:
        bullet_points = []
    return {
        "name": item.get("title") or "Project",
        "bullet_points": bullet_points,
        "date": str(item.get("date") or ""),
        "link": item.get("url"),
    }


def merge_projects(portfolio: dict[str, Any], items: list[dict[str, Any]]) -> None:
    projects = portfolio.get("projects") or []
    if not isinstance(projects, list):
        projects = []
        portfolio["projects"] = projects
    existing_names = {
        p.get("name") for p in projects if isinstance(p, dict) and p.get("name")
    }
    for item in items:
        if item.get("type") not in (None, "project", "projects"):
            continue
        proj = portfolio_item_to_project(item)
        if proj["name"] in existing_names:
            continue
        portfolio.setdefault("projects", []).append(proj)
        existing_names.add(proj["name"])


def is_current_resume(doc: dict[str, Any]) -> bool:
    return "content" in doc and "profile_id" in doc


def normalize_current_resume(
    doc: dict[str, Any],
    user_id: ObjectId,
    profile_id: ObjectId,
    portfolio_id: ObjectId,
) -> dict[str, Any]:
    out = copy.deepcopy(doc)
    out["user_id"] = user_id
    out["profile_id"] = profile_id
    out["portfolio_id"] = portfolio_id
    out.pop("user", None)
    out.pop("profile", None)
    out.pop("portfolio", None)
    out.setdefault("job_description", "")
    out.setdefault("cover_letter_ids", [])
    out.setdefault("custom_sections", [])
    out.setdefault("content", {})
    out["created_at"] = _dt(out.get("created_at"))
    out["updated_at"] = _dt(out.get("updated_at"))
    return out


def legacy_to_current_resume(
    doc: dict[str, Any],
    user_id: ObjectId,
    profile_id: ObjectId,
    portfolio_id: ObjectId,
    source: str,
) -> dict[str, Any] | None:
    content = legacy_resume_to_content(doc)
    if not content:
        return None
    title = doc.get("title") or "Recovered resume"
    if doc.get("company_name") or doc.get("job_title"):
        parts = [
            str(doc.get("company_name") or "").replace("_", " ").title(),
            str(doc.get("job_title") or "").replace("_", " ").title(),
        ]
        title = " ".join(p for p in parts if p).strip() or title
    return {
        "_id": doc["_id"],
        "user_id": user_id,
        "profile_id": profile_id,
        "portfolio_id": portfolio_id,
        "title": title,
        "version": doc.get("version") or 1,
        "template_id": doc.get("template_id") or "default",
        "company_name": doc.get("company_name"),
        "job_title": doc.get("job_title"),
        "job_description": doc.get("job_description") or "",
        "content": content,
        "custom_sections": [],
        "resume_pdf_key": None,
        "cover_letter_ids": [],
        "llm_settings": {},
        "llm_usage": doc.get("llm_usage") or {},
        "created_at": _dt(doc.get("created_at")),
        "updated_at": _dt(doc.get("updated_at")),
        "_recovery_source": source,
    }


LEGACY_USER_ID_ALIASES: dict[str, str] = {
    "mujakayadan": "mujakayadan@outlook.com",
    "test_user": "test@example.com",
}

# Captured from local `rbt` before accidental wipe (Firebase Auth still has these UIDs).
KNOWN_FIREBASE_BY_EMAIL: dict[str, str] = {
    "mujakayadan@outlook.com": "oPnuBrhLYnTVMYr4gz5a873RpG53",
    "muhammet.kayadan@gmail.com": "vic0lhaUTfNXrvwY3VNw7HyALkB3",
    "mujakayadan@gmail.com": "8q3GILLvdFSTpGwZe9wEaiuACKF2",
}


def resolve_email_for_document(
    doc: dict[str, Any],
    old_user_to_email: dict[str, str],
    username_to_email: dict[str, str],
) -> str | None:
    """Resolve a document to a canonical email."""
    pi = doc.get("personal_information") or {}
    if isinstance(pi, dict) and pi.get("email"):
        return _email_key(pi["email"])

    for field in ("email",):
        if doc.get(field):
            return _email_key(doc[field])

    uid = doc.get("user_id") or doc.get("user") or doc.get("user_reference")
    if uid is None:
        return None
    uid_str = str(uid)
    if "@" in uid_str:
        return _email_key(uid_str)
    if uid_str in old_user_to_email:
        return old_user_to_email[uid_str]
    if uid_str in username_to_email:
        return username_to_email[uid_str]
    if uid_str in LEGACY_USER_ID_ALIASES:
        return _email_key(LEGACY_USER_ID_ALIASES[uid_str])
    return username_to_email.get(uid_str.lower())


def bootstrap_profile_from_resume(
    resume: dict[str, Any], email: str, user_id: ObjectId
) -> dict[str, Any]:
    pi = copy.deepcopy(resume.get("personal_information") or {})
    pi.setdefault("email", email)
    pi.setdefault("full_name", pi.get("full_name") or email.split("@")[0])
    now = datetime.now(UTC)
    return {
        "_id": ObjectId(),
        "user_id": user_id,
        "personal_information": pi,
        "prompt_preferences": {},
        "system_preferences": {},
        "llm_usage": {},
        "created_at": now,
        "updated_at": now,
        "_recovered_bootstrap": True,
    }


def bootstrap_portfolio_from_resume(
    resume: dict[str, Any], user_id: ObjectId, profile_id: ObjectId
) -> dict[str, Any]:
    now = datetime.now(UTC)
    portfolio: dict[str, Any] = {
        "_id": ObjectId(),
        "user_id": user_id,
        "profile_id": profile_id,
        "career_summary": resume.get("career_summary") or {},
        "skills": resume.get("skills") or [],
        "work_experience": resume.get("work_experience") or [],
        "education": resume.get("education") or [],
        "projects": resume.get("projects") or [],
        "awards": resume.get("awards") or [],
        "publications": resume.get("publications") or [],
        "certifications": [],
        "custom_sections": {"enabled": [], "order": []},
        "created_at": now,
        "updated_at": now,
        "_recovered_bootstrap": True,
    }
    return portfolio


def empty_portfolio(user_id: ObjectId, profile_id: ObjectId) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "_id": ObjectId(),
        "user_id": user_id,
        "profile_id": profile_id,
        "career_summary": {},
        "skills": [],
        "work_experience": [],
        "education": [],
        "projects": [],
        "awards": [],
        "publications": [],
        "certifications": [],
        "custom_sections": {"enabled": [], "order": []},
        "created_at": now,
        "updated_at": now,
        "_recovered_bootstrap": True,
    }


def pick_richer(
    existing: dict[str, Any] | None, candidate: dict[str, Any]
) -> dict[str, Any]:
    if not existing:
        return candidate
    existing_score = len(json.dumps(existing, default=str))
    candidate_score = len(json.dumps(candidate, default=str))
    if candidate_score > existing_score:
        return candidate
    if _dt(candidate.get("updated_at")) > _dt(existing.get("updated_at")):
        return candidate
    return existing


class RecoveryStats:
    def __init__(self) -> None:
        self.users = 0
        self.profiles = 0
        self.portfolios = 0
        self.resumes = 0
        self.resumes_skipped_dup = 0
        self.resumes_skipped_empty = 0
        self.preambles = 0
        self.tex_headers = 0
        self.migrations = 0

    def report(self) -> str:
        return (
            f"users={self.users}, profiles={self.profiles}, portfolios={self.portfolios}, "
            f"resumes={self.resumes} (skipped dup={self.resumes_skipped_dup}, "
            f"empty={self.resumes_skipped_empty}), preambles={self.preambles}, "
            f"tex_headers={self.tex_headers}, migrations={self.migrations}"
        )


def recover(
    source_uri: str,
    target_uri: str,
    target_db_name: str,
    dry_run: bool,
) -> RecoveryStats:
    stats = RecoveryStats()
    client = MongoClient(source_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")

    sources: dict[str, Database] = {
        name: client[name]
        for name in SOURCE_DBS
        if name in client.list_database_names()
    }
    if not sources:
        raise SystemExit("No source databases found on local MongoDB.")

    users_by_email: dict[str, dict[str, Any]] = {}
    old_user_to_email: dict[str, str] = {}
    username_to_email: dict[str, str] = {}

    for db_name, db in sources.items():
        for raw in db.users.find():
            normalized = normalize_user(raw)
            if not normalized:
                continue
            key = _email_key(normalized["email"])
            if not key:
                continue
            old_user_to_email[str(raw["_id"])] = key
            if normalized.get("username"):
                username_to_email[str(normalized["username"]).lower()] = key
            users_by_email[key] = pick_richer(users_by_email.get(key), normalized)
            users_by_email[key]["_recovery_sources"] = list(
                set(users_by_email[key].get("_recovery_sources", []) + [db_name])
            )

    profiles_by_email: dict[str, dict[str, Any]] = {}

    for db_name, db in sources.items():
        for raw in db.profiles.find():
            email = resolve_email_for_document(
                raw, old_user_to_email, username_to_email
            )
            if not email:
                continue
            migrated = migrate_profile_preferences(raw)
            profiles_by_email[email] = pick_richer(
                profiles_by_email.get(email), migrated
            )
            profiles_by_email[email].setdefault("_recovery_sources", []).append(db_name)

    portfolios_by_email: dict[str, dict[str, Any]] = {}
    old_portfolio_to_email: dict[str, str] = {}
    portfolio_items_by_user: dict[str, list[dict[str, Any]]] = {}

    if "user_information" in sources:
        ui = sources["user_information"]
        for item in ui.portfolio_items.find():
            email = resolve_email_for_document(
                item, old_user_to_email, username_to_email
            )
            if email:
                portfolio_items_by_user.setdefault(email, []).append(item)

    for db_name, db in sources.items():
        for raw in db.portfolios.find():
            email = resolve_email_for_document(
                raw, old_user_to_email, username_to_email
            )
            if not email:
                continue
            profile = profiles_by_email.get(email)
            profile_id = profile.get("_id") if profile else None
            normalized = normalize_portfolio(raw, _oid(profile_id))
            portfolios_by_email[email] = pick_richer(
                portfolios_by_email.get(email), normalized
            )
            portfolios_by_email[email].setdefault("_recovery_sources", []).append(
                db_name
            )
            merge_projects(
                portfolios_by_email[email],
                portfolio_items_by_user.get(email, []),
            )
            old_portfolio_to_email[str(raw["_id"])] = email

    resumes_out: list[dict[str, Any]] = []
    resume_fingerprints: set[str] = set()

    def add_resume(resume: dict[str, Any] | None) -> None:
        if not resume:
            stats.resumes_skipped_empty += 1
            return
        content = resume.get("content") or legacy_resume_to_content(resume)
        if not content:
            stats.resumes_skipped_empty += 1
            return
        resume["content"] = content
        fp = _content_fingerprint(content)
        meta = f"{resume.get('user_id')}|{resume.get('company_name')}|{resume.get('job_title')}|{resume.get('title')}|{fp}"
        if meta in resume_fingerprints:
            stats.resumes_skipped_dup += 1
            return
        resume_fingerprints.add(meta)
        resumes_out.append(resume)

    def ensure_profile_and_portfolio(
        email: str, resume_hint: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        user = users_by_email.get(email)
        if not user:
            return None
        user_id = user["_id"]
        profile = profiles_by_email.get(email)
        if not profile:
            if resume_hint:
                profile = bootstrap_profile_from_resume(resume_hint, email, user_id)
            else:
                profile = bootstrap_profile_from_resume(
                    {
                        "personal_information": {
                            "email": email,
                            "full_name": email.split("@")[0],
                        }
                    },
                    email,
                    user_id,
                )
            profiles_by_email[email] = profile
        portfolio = portfolios_by_email.get(email)
        if not portfolio:
            if resume_hint and any(
                resume_hint.get(k) for k in ("work_experience", "skills", "projects")
            ):
                portfolio = bootstrap_portfolio_from_resume(
                    resume_hint, user_id, profile["_id"]
                )
            else:
                portfolio = empty_portfolio(user_id, profile["_id"])
            portfolios_by_email[email] = portfolio
        return profile, portfolio

    def register_user_from_email(
        email: str, hint: dict[str, Any] | None = None
    ) -> None:
        key = _email_key(email)
        if not key or key in users_by_email:
            return
        firebase_uid = KNOWN_FIREBASE_BY_EMAIL.get(
            key, f"recovered-email-{key.split('@')[0]}"
        )
        users_by_email[key] = {
            "_id": ObjectId(),
            "username": key.split("@")[0],
            "email": key,
            "firebase_uid": firebase_uid,
            "auth_provider": "firebase.password",
            "is_active": True,
            "is_superuser": False,
            "email_verified": False,
            "is_new_user": False,
            "current_setup_step": 99,
            "subscription_status": "free",
            "created_at": _dt(hint.get("created_at")) if hint else datetime.now(UTC),
            "updated_at": _dt(hint.get("updated_at")) if hint else datetime.now(UTC),
            "_recovery_sources": ["resume_derived"],
        }

    for email in KNOWN_FIREBASE_BY_EMAIL:
        register_user_from_email(email, None)

    for _db_name, db in sources.items():
        for coll_name in ("resumes", "resumes_backup"):
            if coll_name not in db.list_collection_names():
                continue
            for raw in db[coll_name].find():
                pi = raw.get("personal_information") or {}
                if isinstance(pi, dict) and pi.get("email"):
                    register_user_from_email(pi["email"], raw)

    for db_name, db in sources.items():
        for raw in db.resumes.find():
            email = resolve_email_for_document(
                raw, old_user_to_email, username_to_email
            )
            if not email or email not in users_by_email:
                continue
            pair = ensure_profile_and_portfolio(email, raw)
            if not pair:
                stats.resumes_skipped_empty += 1
                continue
            profile, portfolio = pair
            user_id = users_by_email[email]["_id"]
            profile_id = profile["_id"]
            portfolio_id = portfolio["_id"]
            if is_current_resume(raw):
                add_resume(
                    normalize_current_resume(raw, user_id, profile_id, portfolio_id)
                )
            else:
                add_resume(
                    legacy_to_current_resume(
                        raw, user_id, profile_id, portfolio_id, db_name
                    )
                )

        if db_name == "user_information":
            for raw in db.resumes_backup.find():
                email = resolve_email_for_document(
                    raw, old_user_to_email, username_to_email
                )
                if not email or email not in users_by_email:
                    continue
                pair = ensure_profile_and_portfolio(email, raw)
                if not pair:
                    continue
                profile, portfolio = pair
                add_resume(
                    legacy_to_current_resume(
                        raw,
                        users_by_email[email]["_id"],
                        profile["_id"],
                        portfolio["_id"],
                        "user_information.resumes_backup",
                    )
                )

    for email in users_by_email:
        ensure_profile_and_portfolio(email, None)

    taken_usernames: set[str] = set()
    for email, user in sorted(users_by_email.items(), key=lambda x: x[0]):
        user["username"] = _unique_username(email, taken_usernames)

    # Assign consistent _id for users and link profiles/portfolios
    final_users: list[dict[str, Any]] = []
    final_profiles: list[dict[str, Any]] = []
    final_portfolios: list[dict[str, Any]] = []

    for email, user in users_by_email.items():
        user = copy.deepcopy(user)
        user.pop("_recovery_sources", None)
        user.pop("_recovered_bootstrap", None)
        final_users.append(user)

        profile = profiles_by_email.get(email)
        if profile:
            profile = copy.deepcopy(profile)
            profile["user_id"] = user["_id"]
            profile.pop("_recovery_sources", None)
            profile.pop("_recovered_bootstrap", None)
            if not profile.get("personal_information"):
                profile["personal_information"] = {
                    "full_name": user.get("username", ""),
                    "email": user["email"],
                }
            final_profiles.append(profile)
            user_profile_id = profile["_id"]

            portfolio = portfolios_by_email.get(email)
            if portfolio:
                portfolio = copy.deepcopy(portfolio)
                portfolio["user_id"] = user["_id"]
                portfolio["profile_id"] = user_profile_id
                portfolio.pop("_recovery_sources", None)
                portfolio.pop("_recovered_bootstrap", None)
                final_portfolios.append(portfolio)

    for resume in resumes_out:
        resume.pop("_recovery_source", None)

    preambles: dict[Any, dict] = {}
    tex_headers: dict[Any, dict] = {}
    migrations: dict[Any, dict] = {}
    tex_templates: dict[Any, dict] = {}

    for _db_name, db in sources.items():
        for p in db.preambles.find():
            key = (p.get("name"), p.get("type"))
            preambles[key] = pick_richer(preambles.get(key), p)
        for h in db.tex_headers.find():
            key = (h.get("name"), h.get("category"))
            tex_headers[key] = pick_richer(tex_headers.get(key), h)
        for m in db.migrations.find():
            migrations[m.get("_id")] = m
        if "tex_templates" in db.list_collection_names():
            for t in db.tex_templates.find():
                tex_templates[t.get("_id")] = t

    stats.users = len(final_users)
    stats.profiles = len(final_profiles)
    stats.portfolios = len(final_portfolios)
    stats.resumes = len(resumes_out)
    stats.preambles = len(preambles)
    stats.tex_headers = len(tex_headers)
    stats.migrations = len(migrations)

    print(f"Recovery plan ({'dry-run' if dry_run else 'apply'}): {stats.report()}")

    if dry_run:
        print(f"  Sources: {list(sources.keys())}")
        print(f"  Target: {target_uri} / {target_db_name}")
        client.close()
        return stats

    target_client = MongoClient(target_uri, serverSelectionTimeoutMS=10000)
    target_client.admin.command("ping")
    target_db = target_client[target_db_name]

    collections_to_replace = [
        "users",
        "profiles",
        "portfolios",
        "resumes",
        "cover_letters",
        "preambles",
        "tex_headers",
        "migrations",
        "tex_templates",
    ]
    for coll in collections_to_replace:
        if coll in target_db.list_collection_names():
            target_db[coll].delete_many({})

    if final_users:
        target_db.users.insert_many(final_users)
    if final_profiles:
        target_db.profiles.insert_many(final_profiles)
    if final_portfolios:
        target_db.portfolios.insert_many(final_portfolios)
    if resumes_out:
        target_db.resumes.insert_many(resumes_out)
    if preambles:
        target_db.preambles.insert_many(list(preambles.values()))
    if tex_headers:
        target_db.tex_headers.insert_many(list(tex_headers.values()))
    if migrations:
        target_db.migrations.insert_many(list(migrations.values()))
    if tex_templates:
        target_db.tex_templates.insert_many(list(tex_templates.values()))

    client.close()
    target_client.close()
    print(f"Recovery written to {target_uri} database '{target_db_name}'.")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover MongoDB from local sources.")
    parser.add_argument(
        "--source-uri",
        default=DEFAULT_TARGET_URI,
        help="MongoDB URI for source DBs (default: localhost)",
    )
    parser.add_argument(
        "--target-uri",
        default=None,
        help="MongoDB URI to write merged data (default: same as source-uri)",
    )
    parser.add_argument(
        "--target-db",
        default=DEFAULT_TARGET_DB,
        help="Target database name (default: rbt)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts only; do not write",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Print source DB relationships and exit",
    )
    args = parser.parse_args()
    if args.analyze:
        analyze_gaps(args.source_uri)
        return
    target_uri = args.target_uri or args.source_uri

    try:
        recover(args.source_uri, target_uri, args.target_db, args.dry_run)
    except Exception as exc:
        import traceback

        traceback.print_exc()
        print(f"Recovery failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def analyze_gaps(source_uri: str = DEFAULT_TARGET_URI) -> None:
    client = MongoClient(source_uri, serverSelectionTimeoutMS=5000)
    for db_name in SOURCE_DBS:
        if db_name not in client.list_database_names():
            continue
        db = client[db_name]
        print(f"\n=== {db_name} ===")
        print("users:", [(u.get("email"), str(u["_id"])) for u in db.users.find()])
        print(
            "profiles:",
            [
                (
                    str(p.get("user_id")),
                    (p.get("personal_information") or {}).get("email"),
                )
                for p in db.profiles.find()
            ],
        )
        print("portfolios:", [str(p.get("user_id")) for p in db.portfolios.find()])
        print("resumes:", db.resumes.count_documents({}))
        sample = db.resumes.find_one()
        if sample:
            print(
                "sample resume user_id:",
                sample.get("user_id"),
                type(sample.get("user_id")),
            )
        if "resumes_backup" in db.list_collection_names():
            print("resumes_backup:", db.resumes_backup.count_documents({}))
    client.close()


if __name__ == "__main__":
    main()
