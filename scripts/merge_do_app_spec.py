"""Merge PRE_DEPLOY migration job into a DigitalOcean app spec YAML file."""

from __future__ import annotations

import subprocess
from pathlib import Path

APP_ID = "3c7ee72f-a17a-4084-9007-24901071ac3f"
OUTPUT = Path(".do/app-spec.live.yaml")

JOBS_BLOCK = """jobs:
- dockerfile_path: Dockerfile
  github:
    branch: main
    deploy_on_push: true
    repo: mujakayadan/yarba-backend
  instance_size_slug: apps-s-1vcpu-0.5gb
  kind: PRE_DEPLOY
  name: db-migrate
  run_command: uv run python scripts/run_migrations.py migrate
  source_dir: /
"""


def main() -> None:
    result = subprocess.run(
        ["doctl", "apps", "spec", "get", APP_ID, "-o", "yaml"],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8")
    if "name: db-migrate" not in text:
        needle = "region: sfo\nservices:"
        if needle not in text:
            raise SystemExit("Could not find insertion point in app spec")
        text = text.replace(needle, f"region: sfo\n{JOBS_BLOCK}services:", 1)

    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    bad = [
        i for i, b in enumerate(text.encode("utf-8")) if b < 32 and b not in (9, 10, 13)
    ]
    if bad:
        raise SystemExit(f"Spec contains {len(bad)} control characters")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
