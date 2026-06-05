# YARBA Backend

**Y**et **A**nother **R**esume **B**uilder **A**pp — FastAPI backend for LaTeX resumes and cover letters, MongoDB/Beanie, Firebase auth, and LLM-assisted content.

## Quick start

**Prerequisites:** Python 3.12, [uv](https://docs.astral.sh/uv/), MongoDB, LaTeX (for PDF generation).

```bash
uv python pin 3.12
uv sync
cp .env.example .env   # edit values
uv run uvicorn api.main:app --reload --reload-dir api --reload-dir config --reload-dir core --reload-dir utils
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
| Git hooks | `uv run pre-commit install` (Ruff + mypy on commit) |

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## Deploy

- **Docker (local):**
  ```bash
  docker build -f Dockerfile.base -t yarba-base .
  docker build --build-arg BASE_IMAGE=yarba-base -t yarba-backend .
  ```
- **DigitalOcean App Platform:** uses slim root `Dockerfile` on top of `ghcr.io/mucahitkayadan/yarba-backend-base`. After changing `Dockerfile.base`, `pyproject.toml`, or `uv.lock`, GitHub Actions rebuilds the base; routine app pushes only copy source (~1–2 min on DO). First-time setup: run **Actions → Build base image → Run workflow**, make the GHCR package public (or add GHCR credentials in App Platform), then deploy.

## Documentation

- [Extended guides (Firebase, LLM services, MongoDB notes)](docs/EXTENDED_README.md)
- [Modernization tracker](docs/MODERNIZATION_TODO.md)
- [Migrations](core/database/migrations/README.md)

## License

MIT
