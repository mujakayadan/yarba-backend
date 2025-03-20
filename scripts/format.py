"""Script to run code formatters (isort and black)."""

import subprocess
import sys
from pathlib import Path


def run_formatters() -> None:
    """Run isort and black formatters on the project."""
    project_root = Path(__file__).parent.parent

    # Run isort
    print("Running isort...")
    isort_result = subprocess.run(
        ["isort", "."],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    # Print isort output
    if isort_result.stdout:
        print(isort_result.stdout)
    if isort_result.stderr:
        print(isort_result.stderr, file=sys.stderr)

    # Run black
    print("Running black...")
    black_result = subprocess.run(
        ["black", "."],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    # Print black output
    if black_result.stdout:
        print(black_result.stdout)
    if black_result.stderr:
        print(black_result.stderr, file=sys.stderr)

    # Exit with appropriate status code
    if isort_result.returncode != 0 or black_result.returncode != 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    run_formatters()
