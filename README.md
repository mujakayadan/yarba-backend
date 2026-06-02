# YARBA Backend

**Y**et **A**nother **R**esume **B**uilder **A**pp — FastAPI backend for LaTeX resumes and cover letters, MongoDB/Beanie, Firebase auth, and LLM-assisted content.

## Quick start

**Prerequisites:** Python 3.12, [uv](https://docs.astral.sh/uv/), MongoDB, LaTeX (for PDF generation).

```bash
uv python pin 3.12
uv sync
cp .env.example .env   # edit values
uv run uvicorn api.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Development

| Task | Command |
|------|---------|
| Tests | `uv run pytest` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Types | `uv run mypy` |
| Migrations | `uv run python scripts/run_migrations.py migrate` |
| Git hooks | `uv run pre-commit install` (Ruff on commit) |

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## Deploy

- **Docker:** `docker build -t yarba-backend .` — runs `uvicorn api.main:app` on port 8000.
- **DigitalOcean App Platform:** uses root `Dockerfile`; legacy `api.py` remains for platform-specific logging if needed.

## Documentation

- [Extended guides (Firebase, LLM services, MongoDB notes)](docs/EXTENDED_README.md)
- [Modernization tracker](docs/MODERNIZATION_TODO.md)
- [Migrations](core/database/migrations/README.md)

## License

MIT
