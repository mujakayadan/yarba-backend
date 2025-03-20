"""Script to run flake8 linting."""

import subprocess
import sys
from pathlib import Path


def run_flake8() -> None:
    """Run flake8 on the project."""
    project_root = Path(__file__).parent.parent

    # Run flake8
    result = subprocess.run(
        ["flake8", "."],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Exit with flake8's status code
    sys.exit(result.returncode)


if __name__ == "__main__":
    run_flake8() 