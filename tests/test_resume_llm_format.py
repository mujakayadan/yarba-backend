"""Tests for resume LLM output schema and serialization."""

from beanie import PydanticObjectId

from core.schemas.resume_schemas import ResumeOutputSchema
from core.utils.json_helper import convert_to_serializable


def test_resume_output_schema_validates_minimal_payload():
    payload = {
        "personal_information": {
            "full_name": "Test User",
            "email": "test@example.com",
        },
        "career_summary": {
            "job_title": "Software Engineer",
            "default_summary": "Five years of backend development.",
        },
        "skills": [{"category": "Languages", "skills": ["Python", "Go"]}],
        "work_experience": [
            {
                "job_title": "Engineer",
                "company": "Acme",
                "location": "Remote",
                "time": "2020 - Present",
                "responsibilities": ["Built APIs"],
            }
        ],
        "education": [
            {
                "degree_type": "B.S.",
                "degree": "Computer Science",
                "university_name": "State University",
                "time": "2016 - 2020",
                "location": "Iowa",
            }
        ],
        "projects": [
            {
                "name": "Yarba",
                "bullet_points": ["Resume automation"],
                "date": "2024",
            }
        ],
        "publications": [
            {
                "name": "Paper",
                "publisher": "Journal",
                "time": "2023",
            }
        ],
        "awards": [
            {
                "name": "Hackathon Winner",
                "explanation": "First place at local hackathon.",
            }
        ],
    }

    model = ResumeOutputSchema.model_validate(payload)
    assert model.personal_information.full_name == "Test User"
    assert model.skills[0].skills == ["Python", "Go"]


def test_convert_to_serializable_handles_object_ids():
    user_id = PydanticObjectId()
    assert convert_to_serializable(user_id) == str(user_id)

    profile_payload = {
        "user_id": user_id,
        "personal_information": {
            "full_name": "Test User",
            "email": "test@example.com",
        },
    }
    serialized_profile = convert_to_serializable(profile_payload)
    assert serialized_profile["user_id"] == str(user_id)
    assert serialized_profile["personal_information"]["email"] == "test@example.com"
