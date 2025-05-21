"""Script to run Ruff linting."""

import subprocess
import sys
from pathlib import Path


def run_ruff_check() -> None:
    """Run ruff check on the project."""
    project_root = Path(__file__).parent.parent

    # Run ruff check
    result = subprocess.run(
        ["ruff", "check", "."],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Exit with ruff's status code
    sys.exit(result.returncode)


if __name__ == "__main__":
    run_ruff_check()
