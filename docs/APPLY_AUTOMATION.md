# Apply automation

Architecture and API contract for Yarba job-application automation. The apply **client** (CLI today; extension or OpenClaw skill later) runs locally; Yarba backend is the brain.

## Phase status

| Phase | Scope | Status |
|-------|--------|--------|
| 0 | Security cleanup (remove server LinkedIn creds) | Done |
| 1 | Agent PAT auth (`yarba_pat_`, scopes) | Done |
| 2 | Application domain (profile, prepare, logging, preferences) | Done |
| 3 | Apply client (local Playwright + LLM CLI) | Done — generic agent + auth/click hardening |
| 4 | yarba.app UI (Agent Access, Applications, Application Settings) | Done |
| 5 | This document + API contract | Done |
| 6 | ATS adapters, MCP, NemoClaw, LinkedIn session | Deferred |

Do not build Phase 6 ATS adapters until a client strategy is chosen. Phase 3 uses generic LLM navigation with human-in-the-loop for CAPTCHA/OTP.

## Architecture

```text
┌─────────────────┐     yarba_pat_      ┌──────────────────┐
│  Apply client   │ ──────────────────► │  Yarba API       │
│  (local browser)│ ◄── prepare payload │  resume, profile │
└────────┬────────┘                     └──────────────────┘
         │
         ▼
   Playwright session (user machine)
   LLM reads page snapshot → fill/click
   Human only for CAPTCHA / OTP / SMS
```

- **Crawl4AI** is used only as a **job-description scraping fallback** in `JobExtractor`, not for form filling.
- **OpenClaw / NemoClaw** are deferred (Phase 6). The CLI is client-agnostic and uses the same REST API a future skill would use.

## Human-in-the-loop (required)

These steps **must not** be automated. The agent uses `action=need_human` and the CLI pauses until the user continues:

| Reason code | User action |
|-------------|-------------|
| `captcha` | Solve CAPTCHA in the browser |
| `email_verification` | Enter email verification code or click link |
| `sms_verification` | Enter SMS code |
| `missing_profile_data` | Add the missing answer in yarba.app → Profile / Application Settings, then continue |

The agent **must not** guess CAPTCHA, OTP, SMS codes, or eligibility/EEO answers.

## What the agent fills automatically

From `ApplicationProfile` (via `POST /applications/prepare`):

| Source | Fields |
|--------|--------|
| `contact` | name, email, phone, address, linkedin, github, website |
| `apply_account_password` | careers-site password (encrypted on profile; PAT needs `applications:credentials:read`) |
| `work_eligibility` | authorization, sponsorship, age, relocation (only if set) |
| `logistics` | salary, start date, notice, referral (only if set) |
| `demographics` | EEO (only if consent + `applications:demographics:read`) |
| Resume narrative | work history, education, skills, projects, cover letter |

If a required form field has **no** matching value in `application_profile`, the agent uses `need_human` with `missing_profile_data` — it does not invent data.

## API quick reference

### Auth

- **Web UI:** Firebase JWT (full access).
- **Apply CLI / agents:** `Authorization: Bearer yarba_pat_...`

Recommended PAT scopes for apply:

```text
applications:read
applications:write
applications:credentials:read
applications:demographics:read   # optional, only if EEO autofill desired
jobs:extract
resumes:read
profiles:read
```

### Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/applications/prepare` | Generate resume + return `application_profile` |
| `GET` | `/applications/profile?resume_id=` | Build profile without new resume |
| `PATCH` | `/applications/{id}` | Update status from client |
| `PUT` | `/profiles/me/application-preferences/apply-credentials` | Store careers password |
| `GET` | `/profiles/me/application-preferences/apply-credentials` | `{ configured: bool }` |

### Encryption

`APPLICATION_DATA_ENCRYPTION_KEY` (Fernet) encrypts demographics and apply credentials at rest. Generate once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store in server env only. Losing the key makes stored secrets unrecoverable.

## CLI usage

```powershell
$env:YARBA_PAT = "yarba_pat_..."
$env:YARBA_API_URL = "http://localhost:8000/api/v1"
uv run python scripts/apply.py --url "https://example.com/jobs/123"
```

| Flag | Meaning |
|------|---------|
| `--submit` | Click final submit (default: dry-run, fill only) |
| `--headless` | No visible browser |
| `--keep-open` | Pause before closing browser |
| `--manual-wait` | Pause before job extraction |
| `--max-steps 40` | LLM loop limit |

Browser profile (cookies/sessions): `%USERPROFILE%\.yarba\apply-browser`

## Privacy

- EEO data is voluntary, encrypted, never used for resume generation.
- Eligibility answers are user attestations; Yarba does not verify them.
- PATs are account master keys — use minimal scopes and expiry.

## Deferred (Phase 6)

- Deterministic ATS adapters (Greenhouse, Lever, Workday)
- OpenClaw skill packaging
- yarba-mcp REST proxy
- LinkedIn Easy Apply via local session only
