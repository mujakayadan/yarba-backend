# MongoDB migrations

Yarba uses timestamped Python migrations tracked in the `migrations` collection.

## Commands

```bash
# Fresh database (CI, local, production deploy job)
uv run python scripts/run_migrations.py migrate

# Check what is applied
uv run python scripts/run_migrations.py status

# New schema change
uv run python scripts/run_migrations.py create --description "short description"

# Existing database that predates migration tracking (one-time bootstrap)
uv run python scripts/run_migrations.py baseline --through <version>

# After squashing history, remove obsolete applied-version rows
uv run python scripts/run_migrations.py prune
```

## Layout

| File | Role |
|------|------|
| `20250608000000_initial_schema.py` | Squashed base schema (collections, validators, indexes) |
| `migration_manager.py` | Runner |
| `schema_helpers.py` | Idempotent `collMod` / index helpers |

New environments run a single `migrate`. The base migration is idempotent: safe on databases that already have collections from earlier incremental migrations.

## Production

The DigitalOcean `db-migrate` PRE_DEPLOY job runs `migrate` before each deploy. Optional `MIGRATIONS_MONGODB_URI` overrides `MONGODB_URI` when the app user lacks `collMod`.

After upgrading from the old incremental migration chain, run once:

```bash
uv run python scripts/run_migrations.py migrate   # applies squashed base if pending
uv run python scripts/run_migrations.py prune     # drops removed version rows
```
