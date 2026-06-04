"""Tests for email body parsing."""

from core.utils.email_body_parser import extract_job_description


def test_extract_job_description_from_plain_text():
    text = (
        "Senior Python Engineer\n\n"
        "We are looking for a backend developer with FastAPI experience. "
        "You will build APIs, work with MongoDB, and deploy to cloud platforms. "
        "Requirements include 5+ years of Python and strong communication skills."
    )
    result = extract_job_description(text)
    assert "Senior Python Engineer" in result
    assert len(result) >= 100


def test_extract_job_description_strips_forwarded_headers():
    text = (
        "---------- Forwarded message ---------\n"
        "From: recruiter@company.com\n"
        "Date: Mon, 1 Jan 2024 10:00:00 -0800\n"
        "Subject: Job opening\n"
        "To: me@example.com\n"
        "\n"
        "Machine Learning Engineer role at Acme Corp. "
        "Build ML pipelines, deploy models, and collaborate with product teams. "
        "Required skills: Python, PyTorch, and cloud experience on AWS or GCP."
    )
    result = extract_job_description(text)
    assert "Forwarded message" not in result
    assert "recruiter@company.com" not in result
    assert "Machine Learning Engineer" in result


def test_extract_job_description_from_html_fallback():
    html = (
        "<html><body><p>Data Scientist position.</p>"
        "<p>Analyze large datasets, build predictive models, and present insights "
        "to stakeholders across the organization on a regular basis.</p></body></html>"
    )
    result = extract_job_description(None, html)
    assert "Data Scientist" in result


def test_extract_job_description_too_short_raises():
    try:
        extract_job_description("Too short.")
        raised = False
    except ValueError:
        raised = True
    assert raised
