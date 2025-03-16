#!/usr/bin/env python
"""
Script to untrack files that are already committed without deleting them.
This is useful for files that should be in .gitignore but were already committed.
"""

import os
import subprocess
import sys


def run_command(command):
    """Run a shell command and return the output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        universal_newlines=True,
    )
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        print(f"Error running command: {command}")
        print(f"Error: {stderr}")
        return None
    return stdout.strip()


def untrack_files(patterns):
    """Untrack files matching the given patterns without deleting them."""
    for pattern in patterns:
        print(f"Untracking files matching pattern: {pattern}")

        # Find files matching the pattern that are tracked by git
        tracked_files = run_command(f'git ls-files "{pattern}"')
        if not tracked_files:
            print(f"No tracked files found matching pattern: {pattern}")
            continue

        files = tracked_files.split("\n")
        print(f"Found {len(files)} tracked files matching pattern: {pattern}")

        # Untrack each file
        for file in files:
            if not file.strip():
                continue

            print(f"Untracking file: {file}")
            result = run_command(f'git rm --cached "{file}"')
            if result is not None:
                print(f"Successfully untracked file: {file}")


def main():
    """Main function."""
    # Patterns to untrack (these should match entries in .gitignore)
    patterns_to_untrack = [
        # Python
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        "*.so",
        ".Python",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "wheels/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        # Virtual environments
        "venv/",
        "env/",
        "ENV/",
        ".env",
        ".venv",
        # IDE specific files
        ".idea/",
        ".vscode/",
        "*.swp",
        "*.swo",
        ".DS_Store",
        # MongoDB
        "*.mongodb",
        "mongodb_data/",
        "dump/",
        # LaTeX
        "*.aux",
        "*.lof",
        "*.log",
        "*.lot",
        "*.fls",
        "*.out",
        "*.toc",
        "*.fmt",
        "*.fot",
        "*.cb",
        "*.cb2",
        ".*.lb",
        "*.dvi",
        "*.xdv",
        "*-converted-to.*",
        "*.pdf",
        "*.ps",
        "*.eps",
        # Project specific
        ".env",
        ".coverage",
        "htmlcov/",
        ".pytest_cache/",
        # Logs
        "logs/",
        "*.log",
    ]

    # Confirm with the user
    print(
        "This script will untrack files that are already committed without deleting them."
    )
    print("The following patterns will be untracked:")
    for pattern in patterns_to_untrack:
        print(f"  - {pattern}")

    confirm = input("Do you want to continue? (y/n): ")
    if confirm.lower() != "y":
        print("Aborting.")
        return

    # Untrack files
    untrack_files(patterns_to_untrack)

    print("\nDone!")
    print("The files have been untracked but not deleted.")
    print("They will now be ignored by git according to your .gitignore file.")
    print("You should commit the .gitignore file and the changes from untracking:")
    print("  git add .gitignore")
    print('  git commit -m "Add .gitignore and untrack ignored files"')


if __name__ == "__main__":
    main()
