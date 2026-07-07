"""Generate display titles for resumes from company and job metadata."""


def generate_resume_title(company_name: str | None, job_title: str | None) -> str:
    """Build a human-readable resume title from company and job fields.

    Stored values may use underscores; each segment is title-cased for display.
    """
    company = (company_name or "").strip()
    job = (job_title or "").strip()

    if not company and not job:
        return "My Resume"

    formatted_company = (
        " ".join(word.capitalize() for word in company.split("_")) if company else ""
    )
    formatted_job = (
        " ".join(word.capitalize() for word in job.split("_")) if job else ""
    )

    if formatted_company and formatted_job:
        return f"{formatted_company} {formatted_job}"
    if formatted_company:
        return formatted_company
    return formatted_job
