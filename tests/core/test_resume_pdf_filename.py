from datetime import UTC, datetime

from core.utils.resume_pdf_filename import build_resume_pdf_filename

FIXED_TS = datetime(2025, 6, 3, 14, 30, 22, tzinfo=UTC)


def test_both_company_and_job_title():
    assert (
        build_resume_pdf_filename(
            "morgan_stanley",
            "ai_engineer",
            timestamp=FIXED_TS,
        )
        == "Morgan_Stanley_Ai_Engineer.pdf"
    )


def test_company_only_includes_timestamp():
    assert (
        build_resume_pdf_filename("morgan_stanley", "", timestamp=FIXED_TS)
        == "Morgan_Stanley_20250603_143022.pdf"
    )


def test_job_title_only_includes_timestamp():
    assert (
        build_resume_pdf_filename(None, "ai_engineer", timestamp=FIXED_TS)
        == "Ai_Engineer_20250603_143022.pdf"
    )


def test_both_missing_uses_timestamp_only():
    assert (
        build_resume_pdf_filename("", None, timestamp=FIXED_TS) == "20250603_143022.pdf"
    )


def test_sanitizes_invalid_filename_characters():
    assert (
        build_resume_pdf_filename("bad*name", "ok_title", timestamp=FIXED_TS)
        == "Badname_Ok_Title.pdf"
    )
