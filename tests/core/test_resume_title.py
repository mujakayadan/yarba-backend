"""Tests for resume title generation."""

from core.utils.resume_title import generate_resume_title


def test_generate_resume_title_from_company_and_job():
    title = generate_resume_title("acme_corp", "backend_engineer")
    assert title == "Acme Corp Backend Engineer"


def test_generate_resume_title_company_only():
    assert generate_resume_title("mbn", None) == "Mbn"


def test_generate_resume_title_job_only():
    assert generate_resume_title(None, "staff_engineer") == "Staff Engineer"


def test_generate_resume_title_empty_values():
    assert generate_resume_title(None, None) == "My Resume"
    assert generate_resume_title("", "") == "My Resume"
