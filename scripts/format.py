"""Script to run Ruff formatter and auto-fixable lint fixes."""

import subprocess
import sys
from pathlib import Path


def run_formatters() -> None:
    """Run ruff format and ruff check --fix on the project."""
    project_root = Path(__file__).parent.parent

    print("Running ruff format...")
    format_result = subprocess.run(
        ["ruff", "format", "."],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if format_result.stdout:
        print(format_result.stdout)
    if format_result.stderr:
        print(format_result.stderr, file=sys.stderr)

    print("Running ruff check --fix...")
    check_result = subprocess.run(
        ["ruff", "check", "--fix", "."],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    if check_result.stdout:
        print(check_result.stdout)
    if check_result.stderr:
        print(check_result.stderr, file=sys.stderr)

    if format_result.returncode != 0 or check_result.returncode != 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    run_formatters()
