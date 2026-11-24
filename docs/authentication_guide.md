# YARBA Authentication Guide

YARBA authenticates with backend-owned passwords and direct Google and Apple
sign-in. Protected API routes accept a Yarba access JWT or an agent personal
access token. Refresh sessions stay in an HttpOnly cookie.

## Password routes

All password routes live under `/api/v1/auth/password`.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/register` | Create an account and set a refresh cookie |
| POST | `/login` | Sign in with email and password |
| POST | `/refresh` | Rotate the refresh cookie and issue a new access token |
| POST | `/logout` | Revoke the current refresh session |
| POST | `/logout-all` | Revoke every refresh session for the user |
| POST | `/forgot-password` | Send a single-use reset link when the account can receive one |
| POST | `/reset-password` | Consume a reset token and set a password |
| POST | `/request-verification` | Send a single-use email verification link |
| POST | `/confirm-verification` | Consume a verification token |
| POST | `/change-password` | Change the current password and revoke refresh sessions |
| POST | `/deactivate` | Deactivate the signed-in account |

Registration and login return a short-lived access token in the JSON body
(`access_token_expires_in` is 900 seconds by default) and set the refresh
cookie. The refresh token is not included in the response body.

```http
POST /api/v1/auth/password/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "YourStrongPassword123",
  "legal_acceptance": {
    "terms_version": "2026-08-19",
    "acceptable_use_version": "2026-08-19",
    "privacy_version": "2026-08-19",
    "ai_data_use_version": "2026-08-19",
    "terms_accepted": true,
    "acceptable_use_accepted": true,
    "privacy_acknowledged": true,
    "ai_data_use_acknowledged": true,
    "minimum_age_confirmed": true,
    "acceptance_surface": "password_registration"
  }
}
```

Send later password and OAuth calls with `credentials: "include"` so the
browser stores and returns the refresh cookie. The cookie name, path, and
SameSite policy come from `REFRESH_COOKIE_*`. The cookie path is
`/api/v1/auth/password`.

Forgot-password and request-verification always return the same message. They
do not reveal whether an account exists.

## OAuth nonce and exchange

Google and Apple routes live under `/api/v1/auth/oauth`.

1. `POST /nonce/google` or `POST /nonce/apple` returns a raw nonce once and
   sets a signed HttpOnly nonce cookie on `/api/v1/auth/oauth`.
2. The first-party client puts that nonce into the provider SDK request.
   Google receives the raw nonce. Apple receives `SHA-256(raw nonce)` as
   lowercase hex.
3. `POST /google` or `POST /apple` sends the provider ID token. The API
   consumes the nonce cookie, verifies the token against the provider JWKS,
   and sets the refresh cookie.

First-time provider sign-in requires `legal_acceptance` with
`acceptance_surface` set to `google_oauth` or `apple_oauth`. An email that
already belongs to another account is not linked automatically.

Configure at least one audience for each provider you enable:

```text
OAUTH_GOOGLE_WEB_AUDIENCES=
OAUTH_GOOGLE_IOS_AUDIENCES=
OAUTH_GOOGLE_ANDROID_AUDIENCES=
OAUTH_APPLE_AUDIENCES=
```

## Calling protected routes

Send the access token as a bearer token:

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

`GET /api/v1/auth/me` returns the signed-in user. `PUT /api/v1/auth/users/me/setup-progress`
updates onboarding progress.

When the access token expires, call `POST /api/v1/auth/password/refresh` with
the refresh cookie. A 401 from a protected route means the access token is
missing, invalid, or expired.

Agent scripts use a personal access token (`Authorization: Bearer yarba_pat_...`)
instead of a user JWT. PAT scope checks live in `require_scopes`.

## Swagger UI

1. Register or log in through `/api/v1/auth/password/register` or
   `/api/v1/auth/password/login`.
2. Copy `access_token` from the response.
3. In Swagger UI, choose **Authorize** and paste the token as a Bearer value.

## Errors

- **401 Unauthorized**: missing, invalid, or expired access token, or bad password
- **403 Forbidden**: the account is inactive, or a personal access token lacks a scope
- **409 Conflict**: registration or provider sign-in cannot use that email
- **422 Unprocessable Entity**: the request body failed validation

Password rules: 8–64 characters with at least one uppercase letter, one
lowercase letter, and one number.
