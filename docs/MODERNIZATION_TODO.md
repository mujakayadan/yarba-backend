# Modernization tracker

## Apply automation (see [APPLY_AUTOMATION.md](APPLY_AUTOMATION.md))

- [x] Phase 0 — Remove LinkedIn env creds and dead server-side apply code
- [x] Phase 1 — Agent PAT auth and scopes
- [x] Phase 2 — ApplicationProfile, JobApplication, prepare, preferences, encryption
- [x] Phase 3 — Local apply CLI (`scripts/apply.py`, generic LLM agent)
- [x] Phase 4 — yarba-frontend Agent Access + Applications + Application Settings
- [x] Phase 5 — Apply automation docs and HITL contract
- [ ] Phase 6 — ATS adapters, OpenClaw skill, MCP, LinkedIn local session (deferred)

## Removed / deprecated

- Server-side LinkedIn credentials (`LINKEDIN_*` env) — removed
- Commented `linkedin_service.py` / `linkedin.py` router — removed
- `core/easy_applier/` — remains gitignored legacy; not revived

## Other modernization

See git history and open issues for stack upgrades (FastAPI, Beanie, Ruff, etc.).
