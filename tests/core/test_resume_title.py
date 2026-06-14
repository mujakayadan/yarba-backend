"""Tests for resume title formatting."""

from core.utils.resume_title import generate_resume_title


def test_generate_resume_title_company_and_job():
    title = generate_resume_title("acme_corp", "backend_engineer")
    assert title == "Acme Corp Backend Engineer"


def test_generate_resume_title_plain_words():
    title = generate_resume_title("Acme", "Engineer")
    assert title == "Acme Engineer"


def test_generate_resume_title_company_only():
    assert generate_resume_title("acme_corp", None) == "Acme Corp"


def test_generate_resume_title_job_only():
    assert generate_resume_title(None, "backend_engineer") == "Backend Engineer"


def test_generate_resume_title_empty():
    assert generate_resume_title(None, None) == "My Resume"
