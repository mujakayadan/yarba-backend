"""Tests for structured work experience dates and ordering."""

import pytest
from pydantic import ValidationError

from core.models.portfolio import WorkExperience, sort_work_experience


def test_work_experience_formats_structured_months() -> None:
    experience = WorkExperience(
        job_title="Engineer",
        start_date="2024-03",
        current=True,
    )

    assert experience.time == "Mar 2024 - Present"


@pytest.mark.parametrize(
    ("start_date", "end_date", "current"),
    [
        ("2024-13", "2025-01", False),
        ("2025-04", "2025-03", False),
        ("2025-04", None, False),
        ("2025-04", "2025-05", True),
        ("9999-01", None, True),
    ],
)
def test_work_experience_rejects_invalid_date_ranges(
    start_date: str,
    end_date: str | None,
    current: bool,
) -> None:
    with pytest.raises(ValidationError):
        WorkExperience(
            start_date=start_date,
            end_date=end_date,
            current=current,
        )


def test_sort_work_experience_handles_structured_and_legacy_dates() -> None:
    experiences = [
        WorkExperience(job_title="Older", time="03/2024 - 03/2025"),
        WorkExperience(job_title="Newest", time="08/25 - 08/26"),
        WorkExperience(
            job_title="Current",
            start_date="2026-07",
            current=True,
        ),
        WorkExperience(job_title="Oldest", time="2019 - 2020"),
    ]

    sorted_experiences = sort_work_experience(experiences)

    assert [experience.job_title for experience in sorted_experiences] == [
        "Current",
        "Newest",
        "Older",
        "Oldest",
    ]
