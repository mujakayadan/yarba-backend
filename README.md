# Resume Builder

A modern resume and cover letter builder with LaTeX output, powered by FastAPI, MongoDB, and Beanie ODM.

## Features

- Create and manage resumes and cover letters
- Generate professional LaTeX documents
- AI-powered content generation
- User authentication and authorization
- Responsive Streamlit UI

## Architecture

This application follows a clean architecture pattern with clear separation of concerns:

- **API Layer**: FastAPI routes and schemas
- **Core Layer**: Business logic and domain models
- **Database Layer**: MongoDB with Beanie ODM
- **UI Layer**: Streamlit interface

## Getting Started

### Prerequisites

- Python 3.10+
- Poetry
- MongoDB

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/resume-builder.git
cd resume-builder
```

2. Install dependencies:

```bash
poetry install
```

3. Set up environment variables:

Create a `.env` file in the project root with the following variables:

```
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=rbt
JWT_SECRET_KEY=your-secret-key
```

### Running the Application

1. Start the API server:

```bash
poetry run uvicorn api.main:app --reload
```

2. Start the Streamlit UI:

```bash
poetry run streamlit run ui/streamlit_app.py
```

## Running the API Server

There are several ways to run the API server:

### Method 1: Using the main.py script directly

```bash
poetry run python api/main.py
```

This will start the API server with default settings.

### Method 2: Using the helper script (recommended)

```bash
poetry run python scripts/run_api.py
```

This provides more options for configuration:

```bash
# Run with auto-reload for development
poetry run python scripts/run_api.py --reload

# Specify host and port
poetry run python scripts/run_api.py --host 0.0.0.0 --port 5000

# Set log level
poetry run python scripts/run_api.py --log-level debug
```

### Method 3: Using uvicorn directly

```bash
poetry run uvicorn api.main:app --reload
```

The API documentation will be available at http://127.0.0.1:8000/docs once the server is running.

## Database Migrations

This project uses Beanie's built-in migration system:

```bash
poetry run python -m scripts.run_migrations
```

## Testing

```bash
poetry run pytest
```

## License

MIT

# Resume Builder MongoDB Improvements

This project contains improvements to the MongoDB data model for the Resume Builder application. The improvements focus on better relationships between collections, proper references, and a more structured approach to data storage.

## Entity Relationship Diagram

The entity relationship diagram can be found in the `design/entity_relationship.md` file. It shows the relationships between the different collections in the MongoDB database.

## Model Improvements

The following improvements have been made to the models:

1. **User Model**:
   - Added helper methods to get related documents (profile, portfolio, resumes)
   - Improved user preferences structure
   - Added additional fields for account management

2. **Profile Model**:
   - Added proper references to the user document
   - Added migration method for personal information
   - Added helper method to get related portfolio

3. **Portfolio Model**:
   - Separated portfolio items into their own collection
   - Added proper references to user and profile documents
   - Added helper methods to get portfolio items by type, tag, etc.

4. **Resume Model**:
   - Added proper references to user and portfolio documents
   - Added support for custom sections
   - Added helper method to get related portfolio

## Migration Scripts

Two migration scripts have been provided to help with the transition to the new data model:

1. **update_mongodb_references.py**:
   - Updates references between documents
   - Ensures consistent user_id references
   - Updates timestamps for consistency

2. **migrate_data.py**:
   - Extracts portfolio items from portfolios and creates separate documents
   - Updates references between collections
   - Migrates personal information from profiles to the new structure
   - Updates timestamps for consistency

## Running the Migration Scripts

To run the migration scripts, follow these steps:

1. Make sure MongoDB is running:
   ```powershell
   & "C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe"
   ```

2. Run the update_mongodb_references.py script:
   ```powershell
   python scripts/update_mongodb_references.py
   ```

3. Run the migrate_data.py script:
   ```powershell
   python scripts/migrate_data.py
   ```

## Benefits of the New Structure

The new structure provides the following benefits:

1. **Better Relationships**: Proper references between documents make it easier to navigate between related data.
2. **Improved Query Performance**: Separate collections for portfolio items allow for more efficient queries.
3. **Backward Compatibility**: The changes maintain backward compatibility with existing data.
4. **Cleaner Code**: Helper methods make it easier to work with related documents.
5. **Better Data Integrity**: Proper references ensure data integrity across collections.

## Next Steps

After running the migration scripts, you should:

1. Update your application code to use the new model structure
2. Test the application thoroughly to ensure everything works as expected
3. Consider adding indexes to improve query performance
4. Add validation rules to ensure data integrity

## Resume Generation Services

The project includes advanced services for generating resumes and cover letters using LLMs.

### LLMService

The `LLMService` provides a unified interface to access various LLM providers through LiteLLM.

#### Features

- Unified access to multiple LLM providers (OpenAI, Anthropic, etc.)
- User-specific configuration based on profile preferences
- Secure API key management
- Methods for generating content for specific resume sections
- Cover letter generation

#### Usage

```python
from core.repositories.profile_repository import ProfileRepository
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService

# Initialize dependencies
profile_repository = ProfileRepository()
prompt_service = PromptService()

# Initialize LLM service
llm_service = LLMService(
    profile_repository=profile_repository,
    prompt_service=prompt_service
)

# Configure for a specific user
await llm_service.configure_for_user("user_id")

# Generate content for a section
work_experience = await llm_service.generate_section(
    section_name="work_experience",
    context=work_experience_data,
    job_description="Software Engineer position..."
)

# Generate a cover letter
cover_letter = await llm_service.generate_cover_letter(
    resume_content=resume_content,
    job_description="Software Engineer position...",
    company_name="Acme Inc.",
    job_title="Senior Software Engineer"
)
```

### ResumeGenerationService

The `ResumeGenerationService` orchestrates the complete resume and cover letter generation process, integrating various repositories and services.

#### Features

- End-to-end resume generation
- Cover letter generation
- LaTeX generation for both resumes and cover letters
- User-specific configuration
- Section-by-section content processing

#### Usage

```python
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.latex_service import LatexService

# Initialize repositories and services
portfolio_repository = PortfolioRepository()
profile_repository = ProfileRepository()
resume_repository = ResumeRepository()

prompt_service = PromptService()
llm_service = LLMService(
    profile_repository=profile_repository,
    prompt_service=prompt_service
)

# Initialize resume generation service
resume_service = ResumeGenerationService(
    resume_repository=resume_repository,
    portfolio_repository=portfolio_repository,
    profile_repository=profile_repository,
    llm_service=llm_service,
)

# Configure for a specific user
await resume_service.configure_for_user("user_id")

# Generate resume content
resume_content = await resume_service.generate_resume_content("resume_id")

# Generate resume LaTeX
resume_latex = await resume_service.generate_latex(
    resume_id="resume_id",
    content=resume_content,
)

# Generate cover letter
cover_letter = await resume_service.generate_cover_letter(
    resume_id="resume_id",
    resume_content=resume_content
)

# Generate cover letter LaTeX
cover_letter_latex = await resume_service.generate_latex(
    resume_id="resume_id",
    content=cover_letter,
    is_cover_letter=True
)
```

## Example Scripts

The project includes several example scripts to demonstrate the usage of various services:

- `scripts/examples/generate_resume.py`: Shows how to generate a resume and cover letter
- `scripts/examples/api_usage.py`: Demonstrates integration with FastAPI
- `scripts/examples/streamlit_ui.py`: Illustrates how to use the services with Streamlit
- `scripts/examples/batch_processing.py`: Shows how to process multiple resumes for multiple users

### Running the Example Scripts

```bash
# Generate a resume
poetry run python scripts/examples/generate_resume.py

# Run the Streamlit UI
poetry run streamlit run scripts/examples/streamlit_ui.py
```

## Prerequisites

- Python 3.10+
- Poetry for dependency management
- MongoDB database
- LaTeX installation for document generation
- API keys for LLM providers (OpenAI, Anthropic, etc.)

## TODO

- LLM should return list of items instead of Latex embeddings to reduce token usage.
- LLM parameters are hard coded for now
