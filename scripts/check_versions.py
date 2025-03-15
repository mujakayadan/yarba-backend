"""
Script to check the versions of key dependencies.
"""

import importlib.metadata
import sys


def main():
    """Check versions of key dependencies."""
    dependencies = [
        "beanie",
        "motor",
        "pydantic",
        "pymongo",
        "fastapi",
    ]

    print("Dependency Versions:")
    print("=" * 50)

    for dep in dependencies:
        try:
            version = importlib.metadata.version(dep)
            print(f"{dep}: {version}")
        except importlib.metadata.PackageNotFoundError:
            print(f"{dep}: Not installed")

    print("\nPython Version:")
    print("=" * 50)
    print(f"Python: {sys.version}")


if __name__ == "__main__":
    main()
