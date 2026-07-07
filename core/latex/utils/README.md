# JSON Schema to LaTeX Conversion

This module provides utilities for converting structured JSON data to LaTeX format.

## Overview

The JSON-to-LaTeX converter allows the system to handle structured data from LLM responses and convert them directly to LaTeX format according to predefined templates. This integration enables:

1. **Structured Data Processing**: Handles JSON schema responses from LLM services
2. **Schema Validation**: Validates the structure of incoming data
3. **Format Conversion**: Converts JSON schemas to LaTeX commands
4. **Fallback Mechanisms**: Falls back to text processing when JSON data is invalid

## Core Components

- `parse_json_content()`: Parses JSON strings or passes through already parsed objects
- `process_content_by_section()`: Main entry point to process content based on section name
- Section processors for each resume component:
  - `process_personal_information()`
  - `process_career_summary()`
  - `process_skills()`
  - `process_work_experience()`
  - `process_education()`
  - `process_projects()`
  - `process_awards()`
  - `process_publications()`

## Data Flow

1. LLM Service returns JSON schema data in response to prompts
2. Resume Generation Service passes this data to the LaTeX Service
3. LaTeX Service uses the JSON-to-LaTeX converter to process each section
4. Processed LaTeX sections are assembled into a complete document
5. The document is compiled to PDF

## Schema Examples

### Personal Information

```json
{
  "full_name": "John Smith",
  "email": "john.smith@example.com",
  "phone": "555-123-4567",
  "address": "San Francisco, CA",
  "linkedin": "https://www.linkedin.com/in/johnsmith/",
  "github": "https://github.com/johnsmith",
  "website": "https://www.johnsmith.dev"
}
```

### Career Summary

```json
{
  "job_titles": ["Machine Learning Engineer", "AI Developer"],
  "years_of_experience": "5",
  "default_summary": "implementing machine learning solutions for industrial applications..."
}
```

### Work Experience

```json
{
  "work_experience": [
    {
      "job_title": "Senior Software Engineer",
      "company": "Tech Corp",
      "location": "San Francisco, CA",
      "time": "2020-2023",
      "responsibilities": [
        "Led development of cloud-based ML platform",
        "Reduced inference time by 40% through optimization"
      ]
    }
  ]
}
```

## Integration with LaTeX Templates

The converter works with LaTeX templates stored in the database. Each JSON schema field is mapped to corresponding LaTeX commands:

- Personal information → `\personalinfo{name}{phone}{email}{linkedin}{github}{website}{location}`
- Career summary → `\careerSummary{job_title}{years_of_experience}{summary_text}`
- Skills → `\resumeSkillHeading{category}{skills_list}`
- Work experience → `\resumeSubheading{job_title}{time}{company}{location}`
- Education → `\resumeEducationHeading{university}{location}{degree}{time}{courses}`
- Projects → `\resumeProjectHeading{name}{date}`
- Awards → `\resumeAwardHeading{name}{explanation}`
- Publications → `\resumeProjectHeading{name}{time}`

## Fallback Behavior

If JSON parsing fails, the system will attempt to:
1. Use the raw string as the content
2. Sanitize the content to ensure LaTeX compatibility
3. Log the error for debugging
