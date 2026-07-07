# Security Policy

## Reporting a vulnerability

If you discover a security issue in YARBA Backend, please report it responsibly.

**Do not** open a public GitHub issue for security vulnerabilities.

Instead, email **mujakayadan@outlook.com** with:

- A description of the issue and its potential impact
- Steps to reproduce (proof of concept if available)
- Affected endpoints, versions, or configuration
- Your contact information (optional, for follow-up)

We aim to acknowledge reports within **3 business days** and will work with you on a fix and coordinated disclosure when appropriate.

## Supported versions

Security fixes are applied to the active development branch and the latest production deployment. Older releases are not maintained separately.

## Scope

The following are in scope for this policy:

- This repository (`yarba-backend`) and its deployed API
- Authentication, authorization, and data access controls
- File upload, storage, and PDF generation paths
- Webhook endpoints (e.g. inbound email)

Out of scope:

- Third-party services (Firebase, MongoDB Atlas, AWS, Resend, LLM providers, Vercel)
- Social engineering or physical attacks
- Denial-of-service testing against production without prior agreement

## Security practices

### Authentication and authorization

- API routes require a valid **Bearer** token (Firebase ID token or server-issued JWT).
- Resources are scoped to the authenticated user; cross-user access returns `403 Forbidden`.
- Firebase tokens are verified server-side via the Firebase Admin SDK.
- JWTs are signed with `JWT_SECRET_KEY` (HS256). Use a long, random secret in production.

### Secrets and configuration

- Never commit `.env`, `.env.local`, Firebase service account JSON, or API keys.
- Use `.env.example` as a template only; rotate any credential that was ever committed.
- Production secrets belong in your hosting provider's secret store (e.g. DigitalOcean App Platform env vars).

### Network and API hardening

- **CORS** is restricted via `API_CORS_ORIGINS`; do not set `*` in production.
- **Rate limiting** is enabled on API routes, with stricter limits on PDF generation endpoints.
- Request/response body logging is disabled by default to avoid leaking sensitive data.
- Inbound webhooks (Resend) should have `RESEND__WEBHOOK_SECRET` set so signatures are verified.

### Storage

- User uploads (profile pictures, resumes) are stored in S3 (or local storage in development).
- Prefer presigned URLs or API-proxied downloads where browser CORS would otherwise expose buckets.

### Development

- The Firebase test-mode bypass in auth middleware is only active when `ENV=development` and `DEBUG=true`. Never enable this in production.
- Do not run the API with default `JWT_SECRET_KEY` outside local development.

## Safe disclosure

When testing, use a local or staging environment when possible. If you must test against production:

- Do not access, modify, or exfiltrate data belonging to other users.
- Do not degrade service availability.
- Stop testing once you have confirmed the issue and contact us with your findings.

## Recognition

We appreciate researchers who report issues responsibly. With your permission, we may acknowledge your contribution when a fix is released.
