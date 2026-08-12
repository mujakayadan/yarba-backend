# Contributing

## Prerequisites

- Python 3.12 ([uv](https://docs.astral.sh/uv/) recommended)
- MongoDB for full integration tests

## Setup

```bash
uv python pin 3.12
uv sync
uv run playwright install chromium
cp .env.example .env
# edit .env
```

## Git hooks

```bash
uv run pre-commit install
```

On `git commit`: Ruff, mypy, and generic file checks (same quality bar as CI).

If you previously installed a pre-push hook, remove it:

```bash
uv run pre-commit uninstall --hook-type pre-push
```

Manual run: `uv run pre-commit run --all-files`

## Quality checks

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
uv run pre-commit run --all-files
```

CI runs the same steps on push and pull requests.

## Migrations

```bash
uv run python scripts/run_migrations.py status
uv run python scripts/run_migrations.py migrate
```

See [core/database/migrations/README.md](core/database/migrations/README.md).

## Community and security

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md);
do not open a public issue for security-sensitive findings.

Contributions are accepted under the repository's
[Elastic License 2.0](LICENSE).
