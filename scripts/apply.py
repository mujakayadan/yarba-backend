"""Apply to a job posting using a Yarba PAT and browser automation."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import configure_logging, get_logger
from core.apply_client.api_client import YarbaApplyApiError
from core.apply_client.hitl import human_assistance_message
from core.apply_client.runner import ApplyExtractionError, run_apply

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto-apply to a job using Yarba prepare + browser agent.",
    )
    parser.add_argument("--url", required=True, help="Job posting URL to apply to")
    parser.add_argument(
        "--token",
        default=os.environ.get("YARBA_PAT", ""),
        help="yarba_pat_ token (or set YARBA_PAT)",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("YARBA_API_URL", "http://localhost:8000/api/v1"),
        help="Yarba API base URL",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Actually click submit (default is dry-run: fill but do not submit)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (default is headed so you can review)",
    )
    parser.add_argument("--max-steps", type=int, default=40)
    parser.add_argument("--model", default=None, help="Override LLM model")
    parser.add_argument(
        "--manual-wait",
        action="store_true",
        help="Pause for Enter before extraction (default is fully automatic)",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="After the run, keep the browser open until you press Enter in the terminal",
    )
    return parser


async def _main(args: argparse.Namespace) -> int:
    if not args.token:
        logger.error("Missing token. Pass --token or set YARBA_PAT.")
        return 1

    async def pause_before_agent() -> None:
        await asyncio.to_thread(
            input,
            "Press Enter in THIS terminal when the posting is ready (or to continue anyway)... ",
        )

    async def pause_for_human(reason: str) -> None:
        message = human_assistance_message(reason)
        await asyncio.to_thread(
            input,
            f"\n[HUMAN STEP] {message}\nPress Enter here when done to continue...\n",
        )

    async def pause_for_review() -> None:
        await asyncio.to_thread(
            input,
            "Run complete. Press Enter here to close the browser... ",
        )

    try:
        result = await run_apply(
            api_base_url=args.api_url,
            token=args.token,
            job_url=args.url,
            headed=not args.headless,
            submit=args.submit,
            max_steps=args.max_steps,
            model=args.model,
            on_before_agent=pause_before_agent
            if args.manual_wait and not args.headless
            else None,
            on_review=pause_for_review
            if args.keep_open and not args.headless
            else None,
            on_human_required=pause_for_human if not args.headless else None,
        )
    except ApplyExtractionError as exc:
        logger.error("%s", exc)
        return 1
    except YarbaApplyApiError as exc:
        logger.error("Yarba API error: %s", exc)
        return 1
    except Exception:
        logger.exception("Apply run failed")
        return 1

    logger.info(
        "Done. application_id=%s status=%s outcome=%s submit=%s",
        result["application_id"],
        result["status"],
        result["outcome"],
        result["submit"],
    )
    return 0 if result["status"] != "failed" else 2


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()
