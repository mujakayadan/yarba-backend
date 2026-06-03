"""Print filesystem paths that change under the repo (dev diagnostic for uvicorn --reload noise).

Usage:
    uv run python scripts/watch_changes.py
    uv run python scripts/watch_changes.py --seconds 30
    uv run python scripts/watch_changes.py --root . --seconds 15

Run in a second terminal while ``uvicorn --reload`` is running, or alone to see
what else (IDE, tools) is touching files.
"""

from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

from watchfiles import watch


def _rel(path: str, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except ValueError:
        return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("."), help="Directory to watch"
    )
    parser.add_argument("--seconds", type=float, default=20.0, help="How long to watch")
    parser.add_argument(
        "--uvicorn",
        action="store_true",
        help="Use watch_filter=None like uvicorn --reload (no .venv/.mypy_cache ignores)",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    counts: Counter[str] = Counter()
    deadline = time.monotonic() + args.seconds

    print(f"Watching {root} for {args.seconds}s (Ctrl+C to stop early)")
    if args.uvicorn:
        watch_filter = None
        print("(uvicorn mode: watch_filter=None — same as --reload)\n")
    else:
        from watchfiles import DefaultFilter

        watch_filter = DefaultFilter()
        print(
            "(default watchfiles filter: ignores .venv, .mypy_cache, __pycache__, …)\n"
        )

    for changes in watch(
        str(root),
        watch_filter=watch_filter,
        debounce=50,
        step=200,
        stop_event=None,
        yield_on_timeout=True,
    ):
        if changes:
            for kind, raw in changes:
                rel = _rel(raw, root)
                counts[f"{kind.name}: {rel}"] += 1
                print(f"{kind.name:8} {rel}")

        if time.monotonic() >= deadline:
            break

    if not counts:
        print("\nNo changes detected.")
        return

    print("\n--- summary (most frequent) ---")
    for key, n in counts.most_common(30):
        print(f"{n:4}x  {key}")


if __name__ == "__main__":
    main()
