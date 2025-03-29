# JSON Schema Output for LLM Responses

This document describes how to use the JSON schema output feature in the Resume Builder application.

## Overview

The Resume Builder now supports structured JSON output from LLM models, which provides several advantages:

1. **Structured Data**: Instead of receiving LaTeX-formatted text that needs further processing, you get structured data objects
2. **Schema Validation**: Responses are validated against Pydantic models to ensure data integrity
3. **Improved Processing**: Working with JSON objects is typically easier than parsing text
4. **Model Compatibility**: Works with models that support JSON schema (like OpenAI, Anthropic, and Google models)
5. **Direct Database Mapping**: Schema models align with the database models for easier integration
6. **Default Values**: The system provides sensible defaults for required fields if they're missing

## Where JSON Schemas Are Used

The JSON schema system is primarily used in two places:

1. **LLM Service**: The LLM service uses the schemas to structure output from language models
   - Used in the `get_structured_completion()` method
   - Used in the `generate_section()` method when `use_json_schema=True`

2. **Prompt Templates**: Schemas help inform the prompts about expected output structure
   - Each section prompt can include an example of the expected JSON format
   - See the awards prompt for an example of how to structure prompts for JSON output

Preferences are handled differently - they are retrieved directly from application settings
and not generated via LLM responses.

## How It Works

When enabled, the LLM service will:

1. Check if the model supports JSON mode
2. If supported, it will use the full schema capabilities
3. If not fully supported but basic JSON is available, it will use that
4. If JSON is not supported at all, it will fallback to text mode and try to parse results (when fallback is enabled)

## Available Schema Models

The following schema models are available in `core.schemas` and match the corresponding database models:

| Schema | Description | Database Equivalent |
|--------|-------------|---------------------|
| `PersonalInformationSchema` | Personal contact information | `PersonalInformation` |
| `AwardSchema` | Single award entry | `Award` |
| `AwardsListSchema` | List of awards | `List[Award]` |
| `ProjectSchema` | Single project entry | `Project` |
| `ProjectsListSchema` | List of projects | `List[Project]` |
| `SkillSchema` | Skill category with skills | `Skill` |
| `SkillsListSchema` | List of skill categories | `List[Skill]` |
| `WorkExperienceSchema` | Single work experience entry | `WorkExperience` |
| `WorkExperienceListSchema` | List of work experiences | `List[WorkExperience]` |
| `EducationSchema` | Single education entry | `Education` |
| `EducationListSchema` | List of education entries | `List[Education]` |
| `PublicationSchema` | Single publication entry | `Publication` |
| `PublicationsListSchema` | List of publications | `List[Publication]` |
| `CareerSummarySchema` | Career summary information | `CareerSummary` |

## Schema Mapping Utility

The `core.utils.schema_mapping` module provides helper functions for mapping schema objects to database models:

```python
from core.utils.schema_mapping import (
    map_personal_info,
    map_awards,
    map_projects,
    map_schema_to_portfolio,
    ensure_profile_has_personal_info
)
```

Key features:

1. **Default Values**: Provides default values for required fields if they're missing
2. **Type Safety**: Checks for correct types before mapping
3. **Consistent Interface**: Common pattern for all schema types
4. **Error Handling**: Gracefully handles None values and wrong types

Example usage:

```python
# Map a schema object to a database model
personal_information = map_personal_info(schema_result)

# Create a profile that's guaranteed to have personal_information
profile = ensure_profile_has_personal_info(profile)

# Map schema result to a portfolio
portfolio = map_schema_to_portfolio(portfolio, "awards", schema_result)
```

## Configuration

JSON schema support can be configured in the settings:

```python
# .env file
ENABLE_JSON_SCHEMA=True
JSON_SCHEMA_VALIDATION=True
JSON_COMPATIBLE_MODELS=["gpt-4", "gpt-4-turbo", "gpt-4o", "claude-3-opus", "claude-3-sonnet", "gemini-1.5-pro"]
```

Or in code:

```python
from config.settings import settings

# Globally
settings.llm.enable_json_schema = True
settings.llm.json_schema_validation = True

# Or in the LLMService constructor
llm_service = LLMService(
    profile_repository=profile_repo,
    prompt_service=prompt_service,
    enable_json_validation=True
)
```

## Usage Examples

### Personal Information

```python
from core.schemas import PersonalInformationSchema
from core.utils.schema_mapping import map_personal_info, ensure_profile_has_personal_info

# Generate personal information
personal_information = await llm_service.get_structured_completion(
    prompt="Generate personal information for John Smith...",
    schema_model=PersonalInformationSchema,
    system_prompt="You are a helpful assistant that outputs structured data.",
    fallback_to_text=True
)

# Map to profile model with default handling
profile_personal_info = map_personal_info(personal_information)

# Get preferences from settings (not generated by LLM)
preferences = Preferences(**settings.preference_settings.model_dump())

# Create or update a profile
profile = Profile(
    user_id=user_id,
    personal_information=profile_personal_info,
    preferences=preferences
)

# Ensure profile has all required fields
profile = ensure_profile_has_personal_info(profile)
await profile.save()
```

### Portfolio Section Generation

```python
from core.schemas import AwardsListSchema
from core.utils.schema_mapping import map_schema_to_portfolio

# Generate section with JSON schema
result = await llm_service.generate_section(
    section_name="awards",
    context=awards_context,
    job_description=job_description,
    use_json_schema=True,
    schema_model=AwardsListSchema
)

# Map schema to portfolio with a single call
portfolio = map_schema_to_portfolio(portfolio, "awards", result)
await portfolio.save()
```

### Direct Structured Completion

```python
from core.schemas import WorkExperienceListSchema
from core.utils.schema_mapping import map_work_experience

structured_result = await llm_service.get_structured_completion(
    prompt="Extract the work experience information...",
    schema_model=WorkExperienceListSchema,
    system_prompt="You are a helpful assistant that outputs data in JSON format.",
    fallback_to_text=True
)

# Map with default handling for missing values
work_experiences = map_work_experience(structured_result)
portfolio.work_experience = work_experiences
```

## Model Compatibility

The following models are known to support JSON schema output:

- OpenAI models: GPT-4 (all variants), GPT-3.5-Turbo (some variants)
- Anthropic: Claude 3 (Opus, Sonnet, Haiku)
- Google: Gemini 1.5 Pro, Gemini 1.0 Pro
- Mistral: Mistral Large

Some models only support basic JSON mode (not full schema):
- Anthropic: Claude 3 Haiku
- OpenAI: Some older GPT-3.5 models

## Fallback Behavior

When a model doesn't support JSON schema or encounters an error:

1. If `fallback_to_text=True` (default), the raw text response is returned
2. If `fallback_to_text=False`, an error will be raised

You can check model support with:

```python
if llm_service.model_supports_json_mode():
    print("JSON mode supported")

if llm_service.model_supports_json_schema():
    print("JSON schema supported")
```

## Best Practices

### 1. Use the Schema Mapping Utility

Always use the schema mapping utility to convert schema objects to database models:

```python
from core.utils.schema_mapping import map_personal_info, map_schema_to_portfolio

# For individual sections
personal_information = map_personal_info(schema_result)

# For multiple portfolio sections at once
portfolio = map_schema_to_portfolio(portfolio, "awards", schema_result)
```

### 2. Ensure Required Fields Have Defaults

Make sure profiles have required fields by using the helper functions:

```python
from core.utils.schema_mapping import ensure_profile_has_personal_info

# Ensure profile has personal_information
profile = ensure_profile_has_personal_info(profile)
```

### 3. Get Preferences From Settings

Always get preferences from settings rather than generating them with LLM:

```python
from config.settings import settings
from core.models.profile import Preferences

def create_preferences_from_settings():
    # Get the default preference settings
    pref_settings = settings.preference_settings

    # Create a Preferences object using the settings values
    preferences = Preferences(
        project_details={
            "max_projects": pref_settings.project_max_projects,
            "bullet_points_per_project": pref_settings.project_bullet_points_per_project
        },
        # ... other preference fields
    )

    return preferences
```

### 4. Type Checking

Always check the type of the result before trying to access properties:

```python
result = await llm_service.generate_section(
    section_name="projects",
    context=context,
    job_description=job_description,
    use_json_schema=True,
    schema_model=ProjectsListSchema
)

if isinstance(result, ProjectsListSchema):
    # Process structured data
    projects = result.projects
else:
    # Process text fallback
    # This might happen with models that don't support JSON output
    text_content = result
```

### 5. Error Handling

Handle potential errors during schema validation:

```python
try:
    result = await llm_service.get_structured_completion(
        prompt=prompt,
        schema_model=EducationListSchema,
        fallback_to_text=False  # Will raise error if schema validation fails
    )
    # Process result
except ValueError as e:
    # Handle schema validation error
    logger.error(f"Schema validation failed: {e}")
    # Fallback to text mode
    result = await llm_service.get_completion(prompt=prompt)
```

## Implementation Details

The feature uses LiteLLM's JSON mode support. For models that don't support JSON output natively, client-side validation can be enabled with `litellm.enable_json_schema_validation = True`.

See the full examples in:
- `examples/portfolio_json_schema.py` - For portfolio section generation
- `examples/personal_info_json_schema.py` - For personal information generation
