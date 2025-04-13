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
  },
  "preferences": {
    // Optional preferences object
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
  "section_preferences": { /* optional object */ }
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
  "title": "string",
  "template_id": "string",
  "job_description": "string (optional)",
  "selected_sections": {
    "personal_information": "Hardcode|Process",
    "career_summary": "Hardcode|Process",
    "skills": "Hardcode|Process",
    "work_experience": "Hardcode|Process",
    "education": "Hardcode|Process",
    "projects": "Hardcode|Process",
    "awards": "Hardcode|Process",
    "publications": "Hardcode|Process",
    "certifications": "Hardcode|Process"
  },
  "llm_preferences": {
    "model": "string",
    "temperature": 0.7
  }
}
```

**Response:** Resume object with generated content

#### Get All Resumes

```
GET /api/v1/resumes
```

Query parameters:
- `skip`: Number of resumes to skip (default: 0)
- `limit`: Number of resumes to return (default: 10, max: 100)
- `title`: Filter by title
- `template_id`: Filter by template ID

**Response:** Array of Resume objects

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

#### Generate Resume Content

```
POST /api/v1/resumes/{resume_id}/generate
```

**Request Body:**
```json
{
  "job_description": "string",
  "selected_sections": ["personal_information", "career_summary", "skills", ...]
}
```

**Response:** Resume object with generated content

#### Get Resume PDF

```
GET /api/v1/resumes/{resume_id}/pdf
```

Query parameters:
- `timeout`: PDF generation timeout in seconds (default: 30, min: 5, max: 60)

**Response:** PDF file

#### Debug PDF Generation

```
POST /api/v1/resumes/{resume_id}/debug-pdf
```

**Response:** Debugging information about PDF generation

## Cover Letter Management

### Cover Letter Endpoints

#### Create Cover Letter

```
POST /api/v1/cover-letters
```

**Request Body:**
```json
{
  "title": "string",
  "template_id": "string",
  "resume_id": "string (optional)",
  "job_description": "string (optional)",
  "recipient_name": "string (optional)",
  "recipient_title": "string (optional)",
  "company_name": "string (optional)",
  "company_address": "string (optional)",
  "llm_preferences": {
    "model": "string",
    "temperature": 0.7
  }
}
```

**Response:** Cover Letter object

#### Get All Cover Letters

```
GET /api/v1/cover-letters
```

Query parameters:
- `skip`: Number of items to skip (default: 0)
- `limit`: Number of items to return (default: 10, max: 100)

**Response:** Array of Cover Letter objects

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
  "title": "string (optional)",
  "template_id": "string (optional)",
  "job_title": "string (optional)",
  "company_name": "string (optional)",
  "job_description": "string (optional)",
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

**Request Body:**
```json
{
  "job_description": "string",
  "resume_id": "string (optional)"
}
```

**Response:** Cover Letter object with generated content

#### Get Cover Letter PDF

```
GET /api/v1/cover-letters/{cover_letter_id}/pdf
```

Query parameters:
- `timeout`: PDF generation timeout in seconds (default: 30, min: 5, max: 60)

**Response:** PDF file

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

## Error Responses

All endpoints may return the following error responses:

- `400 Bad Request`: The request was malformed or invalid
- `401 Unauthorized`: Authentication is required or failed
- `403 Forbidden`: The authenticated user does not have permission
- `404 Not Found`: The requested resource was not found
- `500 Internal Server Error`: An unexpected error occurred
