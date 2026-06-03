"""
Restore portfolio and profile from a Yarba-generated portfolio index.html.

Parses the threejs/modern static site HTML (same structure as website generator output)
and replaces portfolio + profile personal data for a user identified by email.

Usage:
  uv run python scripts/restore_portfolio_from_html.py --dry-run
  uv run python scripts/restore_portfolio_from_html.py
  uv run python scripts/restore_portfolio_from_html.py --html "C:\\path\\to\\index.html"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT / ".env")

from core.database.init import init_db
from core.models.portfolio import (
    CareerSummary,
    CustomSections,
    Education,
    Portfolio,
    Project,
    Skill,
    WorkExperience,
)
from core.models.profile import PersonalInformation, Profile
from core.models.user import User

DEFAULT_HTML = Path(r"C:\Users\Muja\Downloads\index (1).html")
DEFAULT_EMAIL = "mujakayadan@outlook.com"


def _text(el: Tag | None) -> str:
    if not el:
        return ""
    return el.get_text(strip=True)


def _split_degree(degree_line: str) -> tuple[str, str]:
    """Parse '{degree} in {degree_type}' from education-degree heading."""
    marker = " in "
    if marker in degree_line:
        degree, _, degree_type = degree_line.rpartition(marker)
        return degree.strip(), degree_type.strip()
    return degree_line.strip(), ""


def _split_meta(meta: str) -> tuple[str, str]:
    """Parse '{location} • {time}' from education-meta / experience-meta."""
    if "•" in meta:
        location, _, time_part = meta.partition("•")
        return location.strip(), time_part.strip()
    return "", meta.strip()


def _cloudfront_key_from_url(url: str) -> str | None:
    if not url:
        return None
    path = urlparse(url).path.lstrip("/")
    return path or None


def _parse_skill_category(block: Tag) -> Skill | None:
    title_el = block.select_one("h3.skill-category-title:not(.bottom)")
    if not title_el:
        return None
    raw = _text(title_el)
    match = re.match(r"<(.+?)>", raw)
    category = match.group(1) if match else raw.strip("<>/")
    skills = [_text(span) for span in block.select(".skill-name") if _text(span)]
    if not category and not skills:
        return None
    return Skill(category=category, skills=skills)


def parse_portfolio_html(html_path: Path) -> dict[str, Any]:
    """Parse generated index.html into portfolio + profile field dicts."""
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")

    # --- Personal / hero ---
    title = _text(soup.select_one("title")) or "Portfolio"
    profile_img = soup.select_one("img.hero-profile-img")
    profile_picture_url = profile_img.get("src", "") if profile_img else ""
    profile_picture_key = _cloudfront_key_from_url(profile_picture_url)

    typewriter = soup.select_one(".typewriter-text")
    job_titles: list[str] = []
    if typewriter and typewriter.get("data-job-titles"):
        try:
            job_titles = json.loads(typewriter["data-job-titles"])
        except json.JSONDecodeError:
            job_titles = []

    hero_summary_el = soup.select_one(".hero-subtitle b")
    default_summary = _text(hero_summary_el)

    linkedin = github = website = ""
    for link in soup.select(".hero-social-links a[href]"):
        href = link.get("href", "")
        if "linkedin.com" in href:
            linkedin = href
        elif "github.com" in href:
            github = href

    email = DEFAULT_EMAIL
    phone = address = ""
    for item in soup.select("#contact .contact-item"):
        label = _text(item.select_one(".contact-label")).lower()
        value_el = item.select_one(".contact-value")
        if not value_el:
            continue
        if label == "email":
            email = value_el.get("href", "").replace("mailto:", "") or _text(value_el)
        elif label == "phone":
            phone = _text(value_el)
        elif label == "location":
            address = _text(value_el)

    for link in soup.select(".contact-social a[href]"):
        href = link.get("href", "")
        if "linkedin.com" in href and not linkedin:
            linkedin = href
        elif "github.com" in href and not github:
            github = href
        elif (
            href.startswith("http") and "github" not in href and "linkedin" not in href
        ):
            website = href

    personal_info = {
        "full_name": title,
        "email": email,
        "phone": phone or None,
        "address": address or None,
        "linkedin": linkedin or None,
        "github": github or None,
        "website": website or None,
    }

    career_summary = {
        "job_titles": job_titles,
        "default_job_title": job_titles[0] if job_titles else "",
        "years_of_experience": "",
        "default_summary": default_summary,
    }

    # --- Work experience ---
    work_experience: list[dict[str, Any]] = []
    for card in soup.select("#experience .experience-card"):
        header = card.select_one(".experience-header")
        if not header:
            continue
        location, time_part = _split_meta(_text(header.select_one(".experience-meta")))
        responsibilities = [
            _text(li)
            for li in card.select(".experience-list .expandable-item")
            if _text(li)
        ]
        work_experience.append(
            {
                "job_title": _text(header.select_one(".experience-title")),
                "company": _text(header.select_one(".experience-company")),
                "location": location,
                "time": time_part,
                "responsibilities": responsibilities,
            }
        )

    # --- Education ---
    education: list[dict[str, Any]] = []
    for card in soup.select("#education .education-card"):
        header = card.select_one(".education-header")
        if not header:
            continue
        degree_line = _text(header.select_one(".education-degree"))
        degree, degree_type = _split_degree(degree_line)
        location, time_part = _split_meta(_text(header.select_one(".education-meta")))
        gpa_text = _text(header.select_one(".education-gpa"))
        gpa = gpa_text.replace("GPA:", "").strip() if gpa_text else ""
        transcript = [
            _text(li)
            for li in card.select(".transcript-list .expandable-item")
            if _text(li)
        ]
        education.append(
            {
                "degree": degree,
                "degree_type": degree_type,
                "university_name": _text(header.select_one(".education-university")),
                "time": time_part,
                "location": location,
                "GPA": gpa,
                "transcript": transcript,
            }
        )

    # --- Skills ---
    skills: list[dict[str, Any]] = []
    for block in soup.select("#skills .skill-category"):
        skill = _parse_skill_category(block)
        if skill:
            skills.append(skill.model_dump())

    # --- Projects ---
    projects: list[dict[str, Any]] = []
    for card in soup.select("#projects .project-card"):
        header = card.select_one(".project-header")
        if not header:
            continue
        link_el = card.select_one("a.project-link")
        link = link_el.get("href") if link_el else None
        bullet_points = [
            _text(li)
            for li in card.select(".project-description .expandable-item")
            if _text(li)
        ]
        entry: dict[str, Any] = {
            "name": _text(header.select_one(".project-title")),
            "bullet_points": bullet_points,
            "date": _text(header.select_one(".project-date")),
        }
        if link:
            entry["link"] = link
        projects.append(entry)

    return {
        "personal_info": personal_info,
        "profile_picture_key": profile_picture_key,
        "career_summary": career_summary,
        "work_experience": work_experience,
        "education": education,
        "skills": skills,
        "projects": projects,
        "awards": [],
        "publications": [],
        "certifications": [],
        "custom_sections": {"enabled": [], "order": []},
    }


def _build_portfolio_models(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "career_summary": CareerSummary(**parsed["career_summary"]),
        "skills": [Skill(**s) for s in parsed["skills"]],
        "work_experience": [WorkExperience(**w) for w in parsed["work_experience"]],
        "education": [Education(**e) for e in parsed["education"]],
        "projects": [Project(**p) for p in parsed["projects"]],
        "awards": [],
        "publications": [],
        "certifications": [],
        "custom_sections": CustomSections(**parsed["custom_sections"]),
    }


async def restore(
    html_path: Path,
    email: str,
    *,
    dry_run: bool = False,
) -> None:
    parsed = parse_portfolio_html(html_path)
    portfolio_fields = _build_portfolio_models(parsed)

    print(f"Parsed from: {html_path}")
    print(
        f"  work={len(portfolio_fields['work_experience'])}, "
        f"edu={len(portfolio_fields['education'])}, "
        f"skills={len(portfolio_fields['skills'])}, "
        f"projects={len(portfolio_fields['projects'])}"
    )
    print(f"  name={parsed['personal_info']['full_name']!r}")

    if dry_run:
        print("Dry run — no database writes.")
        return

    await init_db()
    user = await User.find_one(User.email == email)
    if not user:
        raise SystemExit(f"User not found for email: {email}")

    profile = await Profile.find_one(Profile.user_id == user.id)
    if not profile:
        raise SystemExit(f"Profile not found for user {user.id}")

    pi = PersonalInformation(**parsed["personal_info"])
    profile.personal_information = pi
    if parsed.get("profile_picture_key"):
        profile.profile_picture_key = parsed["profile_picture_key"]
    profile.updated_at = datetime.now(UTC)
    await profile.save()
    print(f"Updated profile {profile.id}")

    portfolios = await Portfolio.find(Portfolio.user_id == user.id).to_list()
    if len(portfolios) > 1:
        print(f"Deleting {len(portfolios) - 1} duplicate portfolio(s)...")
        for extra in portfolios[1:]:
            await extra.delete()

    portfolio = portfolios[0] if portfolios else None
    now = datetime.now(UTC)
    if portfolio:
        portfolio.career_summary = portfolio_fields["career_summary"]
        portfolio.skills = portfolio_fields["skills"]
        portfolio.work_experience = portfolio_fields["work_experience"]
        portfolio.education = portfolio_fields["education"]
        portfolio.projects = portfolio_fields["projects"]
        portfolio.awards = portfolio_fields["awards"]
        portfolio.publications = portfolio_fields["publications"]
        portfolio.certifications = portfolio_fields["certifications"]
        portfolio.custom_sections = portfolio_fields["custom_sections"]
        portfolio.profile_id = profile.id
        portfolio.updated_at = now
        await portfolio.save()
        print(f"Replaced portfolio {portfolio.id}")
    else:
        portfolio = Portfolio(
            user_id=user.id,
            profile_id=profile.id,
            **portfolio_fields,
            created_at=now,
            updated_at=now,
        )
        await portfolio.insert()
        print(f"Created portfolio {portfolio.id}")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML,
        help="Path to generated index.html",
    )
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="User email")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print counts only",
    )
    args = parser.parse_args()
    if not args.html.is_file():
        raise SystemExit(f"HTML file not found: {args.html}")
    asyncio.run(restore(args.html, args.email, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
