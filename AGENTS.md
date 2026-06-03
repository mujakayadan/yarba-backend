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
