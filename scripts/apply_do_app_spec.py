"""Apply merged app spec to DigitalOcean."""

from __future__ import annotations

import subprocess
from pathlib import Path

APP_ID = "3c7ee72f-a17a-4084-9007-24901071ac3f"
SPEC = Path(".do/app-spec.live.yaml")


def main() -> None:
    if not SPEC.exists():
        raise SystemExit(f"Missing {SPEC}; run scripts/merge_do_app_spec.py first")
    subprocess.run(
        ["doctl", "apps", "update", APP_ID, "--spec", str(SPEC)],
        check=True,
    )
    print("App spec updated; deployment should be in progress.")


if __name__ == "__main__":
    main()
