# ResumeBuilderTeX API Documentation

This document provides an overview of all available API endpoints for the ResumeBuilderTeX application.

## Base URL

All API endpoints are prefixed with `/api/v1`.

## Authentication

The API uses JWT-based authentication. To authenticate, you need to:

1. Register a user account
2. Login to obtain a JWT token
3. Include the token in the `Authorization` header as `Bearer {token}` for protected endpoints

### Authentication Endpoints

#### Register a New User

```
POST /api/v1/auth/register
```

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "full_name": "string"
}
```

**Response:**
```json
{
  "message": "User registered successfully"
}
```

#### Login

```
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

#### Swagger Login (Development Only)

```
POST /api/v1/auth/swagger-login
```

This endpoint is for **development use only** and is disabled in production. It allows testing API endpoints in Swagger UI by providing an ID token.

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "id_token": "string",
  "message": "Use this ID token with the /auth/login endpoint in Swagger UI"
}
```

#### Get Current User Info

```
GET /api/v1/auth/me
```

**Response:**
```json
{
  "id": "string",
  "username": "string",
  "email": "string",
  "is_active": true,
  "is_superuser": false,
  "last_login": "2023-01-01T00:00:00.000Z",
  "last_active": "2023-01-01T00:00:00.000Z"
}
```

#### Forgot Password

```
POST /api/v1/auth/forgot-password
```

**Request Body:**
```json
{
  "email": "string"
}
```

**Response:**
```json
{
  "message": "Password reset instructions sent to your email"
}
```

#### Verify Email

```
POST /api/v1/auth/verify-email
```

**Request Body:**
```json
{
  "email": "string"
}
```

**Response:**
```json
{
  "message": "Email verification instructions sent to your email"
}
```

#### Change Password

```
POST /api/v1/auth/change-password
```

**Request Body:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse. Different endpoints have different rate limits:

- **Default rate limit**: 60 requests per 60 seconds
- **Resume endpoints**: 30 requests per 60 seconds
- **PDF generation endpoints**: 3 requests per 120 seconds

When a rate limit is exceeded, the API will respond with a 429 Too Many Requests status code.

The following headers are included in the response:
- `X-RateLimit-Limit`: The maximum number of requests allowed in the window
- `X-RateLimit-Remaining`: The number of requests remaining in the current window
- `X-RateLimit-Reset`: The time when the current rate limit window resets

## Profile Management

These endpoints manage user profiles containing personal information, preferences, and profile media.

### Profile Endpoints

#### Get Current User Profile

```
GET /api/v1/profiles/me
```

**Response:** Profile object

#### Create Profile

```
POST /api/v1/profiles
```

**Request Body:**
```json
{
  "personal_information": {
    "full_name": "string",
    "email": "string",
    "phone": "string (optional)",
    "address": "string (optional)",
    "linkedin": "string (optional)",
    "github": "string (optional)",
    "website": "string (optional)"
  }
}
```

**Response:** Profile object

#### Update Current User Profile

```
PUT /api/v1/profiles/me
```

**Request Body:**
```json
{
  "personal_information": {
    "full_name": "string (optional)",
    "email": "string (optional)",
    "phone": "string (optional)",
    "address": "string (optional)",
    "linkedin": "string (optional)",
    "github": "string (optional)",
    "website": "string (optional)"
  }
}
```

**Response:** Profile object

#### Patch Current User Profile

```
PATCH /api/v1/profiles/me
```

**Request Body:**
```json
{
  "life_story": "string (optional)",
  "api_keys": { /* optional API keys object */ }
}
```

**Response:** Profile object

#### Update Current User Preferences

```
PUT /api/v1/profiles/me/preferences
```

**Request Body:**
```json
{
  "project_details": { /* optional object */ },
  "work_experience_details": { /* optional object */ },
  "skills_details": { /* optional object */ },
  "career_summary_details": { /* optional object */ },
  "education_details": { /* optional object */ },
  "cover_letter_details": { /* optional object */ },
  "awards_details": { /* optional object */ },
  "publications_details": { /* optional object */ },
  "feature_preferences": { /* optional object */ },
  "notifications": { /* optional object */ },
  "privacy": { /* optional object */ },
  "llm_preferences": { /* optional object */ },
}
```

**Response:** Profile object

#### Patch Current User Preferences

```
PATCH /api/v1/profiles/me/preferences
```

**Request Body:** Same as PUT endpoint, all fields optional

**Response:** Profile object

#### Patch Personal Information

```
PATCH /api/v1/profiles/me/personal-information
```

**Request Body:**
```json
{
  "full_name": "string (optional)",
  "email": "string (optional)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "linkedin": "string (optional)",
  "github": "string (optional)",
  "website": "string (optional)"
}
```

**Response:** Profile object

#### Get Personal Information

```
GET /api/v1/profiles/me/personal-information
```

**Response:**
```json
{
  "full_name": "string",
  "email": "string",
  "phone": "string (optional)",
  "address": "string (optional)",
  "linkedin": "string (optional)",
  "github": "string (optional)",
  "website": "string (optional)"
}
```

#### Get Profile by ID

```
GET /api/v1/profiles/{profile_id}
```

**Response:** Profile object

### Life Story Endpoints

#### Patch Life Story

```
PATCH /api/v1/profiles/me/life-story
```

**Request Body:**
```json
{
  "life_story": "string"
}
```

**Response:** Profile object

#### Get Life Story

```
GET /api/v1/profiles/me/life-story
```

**Response:**
```json
{
  "life_story": "string"
}
```

### Profile Picture Endpoints

#### Upload Profile Picture

```
POST /api/v1/profiles/me/profile-picture
```

**Request:** Multipart form with file upload

**Response:**
```json
{
  "profile_picture_key": "string"
}
```

#### Get Profile Picture Key

```
GET /api/v1/profiles/me/profile-picture
```

**Response:**
```json
{
  "profile_picture_key": "string"
}
```

#### Delete Profile Picture

```
DELETE /api/v1/profiles/me/profile-picture
```

**Response:**
```json
{
  "profile_picture_key": null
}
```

### Signature Endpoints

#### Upload Signature

```
POST /api/v1/profiles/me/signature
```

**Request:** Multipart form with file upload

**Response:**
```json
{
  "signature_key": "string"
}
```

#### Get Signature Key

```
GET /api/v1/profiles/me/signature
```

**Response:**
```json
{
  "signature_key": "string"
}
```

#### Delete Signature

```
DELETE /api/v1/profiles/me/signature
```

**Response:**
```json
{
  "signature_key": null
}
```

## Resume Management

### Resume Endpoints

#### Create Resume

```
POST /api/v1/resumes
```

**Request Body:**
```json
{
  "job_description": "string",
  "compile_pdf": false
}
```

**Response:** Resume object (potentially with generated content/PDF link)

#### Get All Resumes

```
GET /api/v1/resumes
```

Query parameters:
- `skip`: Number of resumes to skip (default: 0)
- `limit`: Number of resumes to return (default: 10, max: 100)
- `sort_by`: Sort field and direction (default: "updated_desc")

**Response:** Paginated list of Resume objects

```json
{
  "items": [Resume objects],
  "total": integer
}
```

#### Get Resumes for Selection

```
GET /api/v1/resumes/list-for-selection
```

Returns a lightweight list of resumes for the current user, containing only the resume ID and a formatted display name (derived from company and job title). This is useful for populating selection interfaces (e.g., dropdowns) without fetching full resume details.

**Query Parameters:**
- `sort_by`: string (optional, default: "updated_desc") - Sort field and direction. Available options: "updated_desc", "updated_asc", "created_desc", "created_asc", "title_asc", "title_desc".

**Response:**
```json
{
  "resumes": [
    {
      "id": "string",
      "resume_name": "string (e.g., Example Corp Software Engineer)"
    },
    {
      "id": "string",
      "resume_name": "string (e.g., Another Org Data Scientist)"
    }
  ]
}
```

#### Get Resume by ID

```
GET /api/v1/resumes/{resume_id}
```

**Response:** Resume object

#### Update Resume

```
PUT /api/v1/resumes/{resume_id}
```

**Request Body:**
```json
{
  "title": "string (optional)",
  "template_id": "string (optional)",
  "job_title": "string (optional)",
  "company_name": "string (optional)",
  "job_description": "string (optional)",
  "content": {
    "personal_information": {...},
    "career_summary": {...},
    "skills": {...},
    "work_experience": {...},
    "education": {...},
    "projects": {...},
    "awards": {...},
    "publications": {...},
    "certifications": {...}
  }
}
```

**Response:** Updated Resume object

#### Delete Resume

```
DELETE /api/v1/resumes/{resume_id}
```

**Response:** HTTP 204 No Content

#### Populate Resume Text Content

```
POST /api/v1/resumes/{resume_id}/populate-text-content
```

Generates or regenerates the full textual content (summary, experience, skills etc.) for an *existing* resume based on its stored job description. Does not handle PDF generation.

**Response:** Resume object with updated textual content.

#### Regenerate Resume (Content and PDF)

```
POST /api/v1/resumes/{resume_id}/regenerate
```

Regenerates the full textual content for an existing resume and optionally recompiles the PDF.

**Query Parameters:**
- `generate_pdf`: boolean (default: true) - Whether to regenerate the PDF as well.

**Response:** Resume object with updated content and potentially updated PDF.

#### Get Resume PDF

```
GET /api/v1/resumes/{resume_id}/pdf
```

Query parameters:
- `timeout`: PDF generation timeout in seconds (default: 30, min: 5, max: 60)

**Response:** PDF URL

```json
{
  "pdf_url": "string"
}
```

#### Upload Resume PDF

```
POST /api/v1/resumes/{resume_id}/upload-pdf
```

**Request:** Multipart form with PDF file upload

**Response:**
```json
{
  "pdf_url": "string"
}
```

#### Delete Resume PDF

```
DELETE /api/v1/resumes/{resume_id}/pdf
```

**Response:**
```json
{
  "pdf_url": null
}
```

#### Get Cover Letters For Resume

```
GET /api/v1/resumes/{resume_id}/cover-letters
```

**Response:** List of Cover Letter objects associated with this resume

```json
[
  {
    "id": "string",
    "user_id": "string",
    "profile_id": "string",
    "portfolio_id": "string",
    "resume_id": "string",
    "template_id": "string",
    "content": {
      "cover_letter_content": "string"
    },
    "has_pdf": boolean,
    "created_at": "2023-01-01T00:00:00.000Z",
    "updated_at": "2023-01-01T00:00:00.000Z"
  }
]
```

#### Debug PDF Generation

```
POST /api/v1/resumes/{resume_id}/debug-pdf
```

**Response:** Debugging information about PDF generation

#### Advanced Debug PDF Generation

```
POST /api/v1/resumes/{resume_id}/advanced-debug
```

**Response:** Detailed debugging information about PDF generation

## Cover Letter Management

Cover letters in this system are directly linked to resumes. Each cover letter must reference a resume, and it automatically inherits the resume's job title, company name, job description, and other metadata. This approach avoids data duplication and ensures consistency. When you create or retrieve a cover letter, the associated resume data is used for PDF generation and content creation.

### Cover Letter Endpoints

#### Create Cover Letter

```
POST /api/v1/cover-letters
```

**Request Body:**
```json
{
  "resume_id": "string",
  "template_id": "string (optional)",
  "generate_pdf": false
}
```

**Response:** Cover Letter object

**Cover Letter Object Structure:**
```json
{
  "id": "string",
  "user_id": "string",
  "profile_id": "string",
  "portfolio_id": "string",
  "resume_id": "string",
  "template_id": "string",
  "content": {
    "cover_letter_content": "string"
  },
  "has_pdf": boolean,
  "created_at": "2023-01-01T00:00:00.000Z",
  "updated_at": "2023-01-01T00:00:00.000Z"
}
```

#### Get All Cover Letters

```
GET /api/v1/cover-letters
```

Query parameters:
- `template_id`: Filter by template ID
- `resume_id`: Filter by resume ID
- `skip`: Number of cover letters to skip (default: 0)
- `limit`: Number of cover letters to return (default: 10, max: 100)
- `sort_by`: Sort field and direction (default: "updated_desc")

**Response:** Paginated list of Cover Letter objects

```json
{
  "items": [Cover Letter objects],
  "total": integer
}
```

#### Get Cover Letter by ID

```
GET /api/v1/cover-letters/{cover_letter_id}
```

**Response:** Cover Letter object

#### Update Cover Letter

```
PUT /api/v1/cover-letters/{cover_letter_id}
```

**Request Body:**
```json
{
  "template_id": "string (optional)",
  "content": {...}
}
```

**Response:** Updated Cover Letter object

#### Delete Cover Letter

```
DELETE /api/v1/cover-letters/{cover_letter_id}
```

**Response:** HTTP 204 No Content

#### Generate Cover Letter Content

```
POST /api/v1/cover-letters/{cover_letter_id}/generate
```

Query parameters:
- `regenerate`: Whether to regenerate content even if it exists (default: false)

**Response:** Cover Letter object with generated content

#### Get Cover Letter PDF

```
GET /api/v1/cover-letters/{cover_letter_id}/pdf
```

Query parameters:
- `timeout`: PDF generation timeout in seconds (default: 30, min: 5, max: 60)
- `regenerate`: Whether to regenerate the PDF even if it exists (default: false)

**Response:** PDF file URL

```json
{
  "pdf_url": "https://storage.example.com/cover-letters/abc123.pdf"
}
```

#### Upload Cover Letter PDF

```
POST /api/v1/cover-letters/{cover_letter_id}/upload-pdf
```

**Request:** Multipart form with PDF file upload

**Response:** PDF file URL

```json
{
  "pdf_url": "https://storage.example.com/cover-letters/abc123.pdf"
}
```

#### Delete Cover Letter PDF

```
DELETE /api/v1/cover-letters/{cover_letter_id}/pdf
```

**Response:**

```json
{
  "pdf_url": null
}
```

## Portfolio Management

### Portfolio Endpoints

#### Get User Portfolio

```
GET /api/v1/portfolios/
```

**Response:** Portfolio object

#### Create Portfolio

```
POST /api/v1/portfolios/
```

**Request Body:**
```json
{
  "profile_id": "string (optional)"
}
```

**Response:** Portfolio object

#### Get Portfolio by ID

```
GET /api/v1/portfolios/{portfolio_id}
```

**Response:** Portfolio object

#### Get Portfolio by Profile ID

```
GET /api/v1/portfolios/by-profile/{profile_id}
```

**Response:** Portfolio object

#### Update Portfolio

```
PUT /api/v1/portfolios/{portfolio_id}
```

**Request Body:**
```json
{
  "profile_id": "string (optional)",
  "professional_title": "string (optional)",
  "career_summary": {
    // Career summary object
  },
  "skills": [
    {
      "category": "string",
      "items": ["string", "string", ...]
    }
  ],
  "work_experience": [
    {
      "company": "string",
      "position": "string",
      "location": "string",
      "start_date": "2023-01",
      "end_date": "2023-12",
      "current": false,
      "description": "string",
      "achievements": ["string", "string", ...]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field_of_study": "string",
      "location": "string",
      "start_date": "2023-01",
      "end_date": "2023-12",
      "current": false,
      "description": "string",
      "courses": ["string", "string", ...]
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string",
      "url": "string",
      "start_date": "2023-01",
      "end_date": "2023-12",
      "current": false,
      "technologies": ["string", "string", ...],
      "achievements": ["string", "string", ...]
    }
  ],
  "awards": [
    {
      "title": "string",
      "issuer": "string",
      "date": "2023-01",
      "description": "string"
    }
  ],
  "publications": [
    {
      "title": "string",
      "publisher": "string",
      "date": "2023-01",
      "url": "string",
      "description": "string",
      "authors": ["string", "string", ...]
    }
  ],
  "certifications": ["string", "string", ...],
  "custom_sections": {
    // Custom sections object
  },
  "version": "string"
}
```

**Response:** Updated Portfolio object

#### Delete Portfolio

```
DELETE /api/v1/portfolios/{portfolio_id}
```

**Response:** HTTP 204 No Content

#### Patch Portfolio (Partial Update)

```
PATCH /api/v1/portfolios/{portfolio_id}
```

**Request Body:**
```json
{
  // Any combination of the following fields can be included
  "profile_id": "string (optional)",
  "professional_title": "string (optional)",
  "career_summary": {
    // Career summary object (optional)
    "job_titles": ["string", "string", ...],
    "years_of_experience": "string",
    "default_summary": "string"
  },
  "skills": [
    // Skills array (optional)
    {
      "category": "string",
      "skills": ["string", "string", ...]
    }
  ],
  "work_experience": [
    // Work experience array (optional)
    {
      "job_title": "string",
      "company": "string",
      "location": "string",
      "time": "string",
      "responsibilities": ["string", "string", ...]
    }
  ],
  "education": [
    // Education array (optional)
    {
      "degree_type": "string",
      "degree": "string",
      "university_name": "string",
      "time": "string",
      "location": "string",
      "GPA": "string",
      "transcript": ["string", "string", ...]
    }
  ],
  "projects": [
    // Projects array (optional)
    {
      "name": "string",
      "bullet_points": ["string", "string", ...],
      "date": "string"
    }
  ],
  "awards": [
    // Awards array (optional)
    {
      "name": "string",
      "explanation": "string"
    }
  ],
  "publications": [
    // Publications array (optional)
    {
      "name": "string",
      "publisher": "string",
      "link": "string",
      "time": "string"
    }
  ],
  "certifications": ["string", "string", ...], // Optional
  "custom_sections": {
    // Custom sections object (optional)
    "enabled": ["string", "string", ...],
    "order": ["string", "string", ...]
  },
  "version": "string" // Optional
}
```

**Response:** Updated Portfolio object

#### Parse Portfolio Document

```
POST /api/v1/portfolios/parse-document
```

Parses an uploaded document (PDF, DOCX) and extracts its content into a structured portfolio data format. This endpoint returns the parsed data, which can then be used to create or update a portfolio. It does not modify any existing portfolio directly.

**Request:** Multipart form-data with a file upload.
- `file`: The document file to be parsed (e.g., a resume in PDF or DOCX format).

**Response:** Parsed portfolio data. The structure matches `PortfolioLLMSchema` but typically excludes database-generated fields like `user_id`, `id`, `created_at`, `updated_at`.

```json
{
  "career_summary": {
    "job_titles": ["string"],
    "default_job_title": "string",
    "years_of_experience": "string",
    "default_summary": "string"
  },
  "skills": [
    {
      "category": "string",
      "skills": ["string"]
    }
  ],
  "work_experience": [
    {
      "job_title": "string",
      "company": "string",
      "location": "string (optional)",
      "time": "string (optional)",
      "responsibilities": ["string"]
    }
  ],
  "education": [
    {
      "degree_type": "string (optional)",
      "degree": "string",
      "university_name": "string",
      "time": "string (optional)",
      "location": "string (optional)",
      "GPA": "string (optional)",
      "transcript": ["string"]
    }
  ],
  "projects": [
    {
      "name": "string",
      "bullet_points": ["string"],
      "date": "string (optional)",
      "link": "string (optional)"
    }
  ],
  "awards": [
    {
      "name": "string",
      "explanation": "string (optional)"
    }
  ],
  "publications": [
    {
      "name": "string",
      "publisher": "string (optional)",
      "link": "string (optional)",
      "time": "string (optional)"
    }
  ],
  "certifications": ["string"],
  "custom_sections": {
    "sections": [
      {
        "title": "string",
        "content": "Union[string, List[str], str (JSON string for complex objects)]"
      }
    ]
  }
  // Note: professional_title might also be part of the top-level response
}
```

#### Section-Specific Portfolio Updates

These endpoints allow updating specific sections of a portfolio independently:

##### Update Career Summary

```
PATCH /api/v1/portfolios/{portfolio_id}/career-summary
```

**Request Body:**
```json
{
  "job_titles": ["Software Engineer", "Machine Learning Engineer"],
  "years_of_experience": "3",
  "default_summary": "in software development, machine learning, and computer vision."
}
```

##### Update Skills

```
PATCH /api/v1/portfolios/{portfolio_id}/skills
```

**Request Body:**
```json
[
  {
    "category": "Languages",
    "skills": ["Python", "C", "C++", "Java"]
  },
  {
    "category": "Frameworks",
    "skills": ["TensorFlow", "PyTorch", "FastAPI"]
  }
]
```

##### Update Work Experience

```
PATCH /api/v1/portfolios/{portfolio_id}/work-experience
```

**Request Body:**
```json
[
  {
    "job_title": "Machine Learning Engineer",
    "company": "Example Corp",
    "location": "Remote",
    "time": "01/2023 - Present",
    "responsibilities": [
      "Developed machine learning models for image recognition",
      "Implemented data pipelines for processing large datasets"
    ]
  }
]
```

##### Update Education

```
PATCH /api/v1/portfolios/{portfolio_id}/education
```

**Request Body:**
```json
[
  {
    "degree_type": "Master's Degree",
    "degree": "Computer Science",
    "university_name": "Example University",
    "time": "2020 - 2022",
    "location": "City, Country",
    "GPA": "3.8",
    "transcript": ["Machine Learning", "Computer Vision", "Advanced Algorithms"]
  }
]
```

##### Update Projects

```
PATCH /api/v1/portfolios/{portfolio_id}/projects
```

**Request Body:**
```json
[
  {
    "name": "AI Project",
    "bullet_points": [
      "Developed a machine learning model for image recognition",
      "Implemented a web interface for easy access to the model"
    ],
    "date": "2023"
  }
]
```

##### Update Awards

```
PATCH /api/v1/portfolios/{portfolio_id}/awards
```

**Request Body:**
```json
[
  {
    "name": "Best Project Award",
    "explanation": "Awarded for innovative approach to AI research"
  }
]
```

##### Update Publications

```
PATCH /api/v1/portfolios/{portfolio_id}/publications
```

**Request Body:**
```json
[
  {
    "name": "Research Paper Title",
    "publisher": "Academic Journal",
    "link": "https://example.com/paper",
    "time": "Jan, 2023"
  }
]
```

**Response for all section-specific updates:** Updated Portfolio object

#### Delete Portfolio Item

```
DELETE /api/v1/portfolios/{portfolio_id}/items/{item_type}/{item_index}
```

**Path Parameters:**
- `portfolio_id`: ID of the portfolio
- `item_type`: Type of item to delete (e.g., "work_experience", "education", "skills")
- `item_index`: Index of the item in the array to delete

**Response:** HTTP 204 No Content

## Health Check

```
GET /api/v1/
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## LinkedIn Integration

> **Note:** LinkedIn integration endpoints are currently commented out in the API implementation and are not available for use. The documentation below is for reference only and will be updated when these endpoints are enabled.

### LinkedIn Credentials

#### Save LinkedIn Credentials

```
POST /api/v1/linkedin/credentials
```

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "message": "LinkedIn credentials saved successfully"
}
```

#### Get LinkedIn Status

```
GET /api/v1/linkedin/status
```

**Response:**
```json
{
  "enabled": true,
  "email": "user@example.com",
  "last_login": "2023-01-01T00:00:00.000Z"
}
```

### LinkedIn Job Search & Applications

#### Search for Jobs

```
POST /api/v1/linkedin/search
```

**Request Body:**
```json
{
  "keywords": "string",
  "location": "string",
  "num_jobs": 10
}
```

**Response:** List of job descriptions

#### Apply for Multiple Jobs

```
POST /api/v1/linkedin/apply
```

**Request Body:**
```json
{
  "job_urls": ["string", "string"],
  "resume_id": "string"
}
```

**Response:** Application results

#### Apply for Single Job

```
POST /api/v1/linkedin/apply/single
```

**Request Body:**
```json
{
  "job_url": "string",
  "resume_id": "string"
}
```

**Response:** Application result

## Error Responses

All endpoints may return the following error responses:

- `400 Bad Request`: The request was malformed or invalid
- `401 Unauthorized`: Authentication is required or failed
- `403 Forbidden`: The authenticated user does not have permission
- `404 Not Found`: The requested resource was not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: An unexpected error occurred

#### Update Prompt Preferences

```
PUT /api/v1/profiles/me/preferences/prompt
```

Updates the user's preferences related to LLM prompt generation (e.g., constraints on generated text sections).

**Request Body:** (`PromptPreferencesUpdate` - all fields optional)
```json
{
  "project": { /* optional: e.g., {"max_projects": 5, "bullet_points_per_project": 4} */ },
  "work_experience": { /* optional: e.g., {"max_jobs": 5, "bullet_points_per_job": 4} */ },
  "skills": { /* optional: e.g., {"max_categories": 6} */ },
  "career_summary": { /* optional: e.g., {"max_words": 30} */ },
  "education": { /* optional: e.g., {"max_entries": 4} */ },
  "cover_letter": { /* optional: e.g., {"paragraphs": 4} */ },
  "awards": { /* optional: e.g., {"max_awards": 5} */ },
  "publications": { /* optional: e.g., {"max_publications": 4} */ }
}
```

**Response:** Profile object

#### Update System Preferences

```
PUT /api/v1/profiles/me/preferences/system
```

Updates the user's system-level preferences (e.g., features, LLM settings, templates).

**Request Body:** (`SystemPreferencesUpdate` - all fields optional)
```json
{
  "features": { /* optional: e.g., {"dark_mode": true} */ },
  "notifications": { /* optional: e.g., {"email_summary": false} */ },
  "privacy": { /* optional: e.g., {"profile_visibility": "private"} */ },
  "llm": { /* optional: e.g., {"model_name": "gpt-4", "temperature": 0.5} */ },
  "templates": { /* optional: e.g., {"default_resume_template_id": "modern"} */ }
}
```

**Response:** Profile object
