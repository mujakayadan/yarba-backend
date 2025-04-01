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

These endpoints manage user profiles containing personal information, skills, education, etc.

### Profile Endpoints

#### Create Profile

```
POST /api/v1/profiles
```

**Request Body:**
```json
{
  "full_name": "string",
  "email": "string",
  "phone": "string",
  "location": "string",
  "website": "string",
  "linkedin": "string",
  "github": "string",
  "summary": "string"
}
```

#### Get Current User Profile

```
GET /api/v1/profiles/me
```

#### Update Profile

```
PUT /api/v1/profiles/{profile_id}
```

**Request Body:** Same as Create Profile, all fields optional

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

#### Get User Portfolios

```
GET /api/v1/portfolios/
```

**Response:** Array of Portfolio objects

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
  "is_active": true,
  "version": "string"
}
```

**Response:** Updated Portfolio object

#### Delete Portfolio

```
DELETE /api/v1/portfolios/{portfolio_id}
```

**Response:** HTTP 204 No Content

#### Delete Portfolio Item

```
DELETE /api/v1/portfolios/{portfolio_id}/items/{item_id}
```

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
