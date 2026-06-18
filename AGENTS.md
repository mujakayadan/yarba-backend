# Agent guide (YARBA backend)

## Stack

- Python 3.12, FastAPI, Beanie/MongoDB, uv, Ruff, mypy, pytest

## Commands

```bash
uv sync
uv run pre-commit install
uv run ruff check . && uv run ruff format .
uv run vulture
uv run mypy
uv run pytest
uv run uvicorn api.main:app --reload --reload-dir api --reload-dir config --reload-dir core --reload-dir utils
```

## Apply CLI (Phase 3)

See [docs/APPLY_AUTOMATION.md](docs/APPLY_AUTOMATION.md) for architecture, API contract, phase status, and human-in-the-loop rules (CAPTCHA / email / SMS verification).

Local browser auto-apply using your PAT (dry-run by default — fills the form but does not submit):

**PowerShell (Windows):**

```powershell
$env:YARBA_PAT = "yarba_pat_..."
$env:YARBA_API_URL = "http://localhost:8000/api/v1"

uv run python scripts/apply.py --url "https://example.com/jobs/123"
uv run python scripts/apply.py --url "..." --submit   # actually submit (use with care)
```

The CLI uses `JobExtractor` locally (Crawl4AI is only a **fallback for scraping job descriptions**), then calls `prepare` on the API. A Playwright + LLM agent drives apply; CAPTCHA and email/SMS verification pause for human input (`need_human`). Store a careers-site password under **Profile → Application Settings**; PATs need `applications:credentials:read`. Flags: `--manual-wait`, `--keep-open`, `--submit`. Browser session: `%USERPROFILE%\\.yarba\\apply-browser`.

Or pass the token inline (avoids persisting it in the shell session):

```powershell
uv run python scripts/apply.py --token "yarba_pat_..." --url "https://example.com/jobs/123"
```

**bash:**

```bash
export YARBA_PAT=yarba_pat_...
export YARBA_API_URL=http://localhost:8000/api/v1
uv run python scripts/apply.py --url "https://example.com/jobs/123"
```

Requires Playwright browsers (`playwright install chromium`) and an LLM key (`OPENAI_API_KEY`, etc.).
Fill **Profile → Application Settings** before running so eligibility answers are available.

## Layout

- `api/` — routes, schemas, middleware
- `core/` — domain models, services, repositories
- `config/` — settings (`config/settings.py`)
- `scripts/` — CLI utilities and migrations runner

## Conventions

- Use `X | None`, `list[X]`, `dict[K, V]` (PEP 604), not `Optional`/`List`/`Dict`
- Pydantic v2: `model_config = ConfigDict(...)`, not nested `class Config`
- Settings fields: `validation_alias` for env names, not deprecated `env=` on `Field`
- Lint/format: Ruff only (no black/isort/flake8)
- Do not commit `.env`, credentials, or generated PDFs

## Modernization tracker

See [docs/MODERNIZATION_TODO.md](docs/MODERNIZATION_TODO.md).
