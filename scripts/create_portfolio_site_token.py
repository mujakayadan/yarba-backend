#!/usr/bin/env python
"""Create a read-only portfolio site token for an external portfolio SPA.

The raw token is printed once; only its SHA-256 hash is stored in MongoDB.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.database.init import init_db
from core.models.portfolio import Portfolio
from core.models.portfolio_site_token import PortfolioSiteToken
from core.models.user import User
from core.utils.portfolio_site_token import generate_raw_token, hash_token


async def create_token(email: str, label: str, revoke_existing: bool) -> None:
    client = await init_db()
    if not client:
        print("Failed to connect to MongoDB.", file=sys.stderr)
        sys.exit(1)

    user = await User.find_one(User.email == email)
    if not user:
        print(f"No user found for email: {email}", file=sys.stderr)
        sys.exit(1)

    portfolio = await Portfolio.find_one(Portfolio.user_id == user.id)
    portfolio_id = portfolio.id if portfolio else None

    if revoke_existing:
        existing = await PortfolioSiteToken.find(
            PortfolioSiteToken.user_id == user.id,
            PortfolioSiteToken.is_active == True,  # noqa: E712
        ).to_list()
        for record in existing:
            record.is_active = False
            record.updated_at = datetime.now(UTC)
            await record.save()
        if existing:
            print(f"Revoked {len(existing)} existing token(s).")

    raw_token = generate_raw_token()
    now = datetime.now(UTC)
    token_record = PortfolioSiteToken(
        token_hash=hash_token(raw_token),
        user_id=user.id,
        portfolio_id=portfolio_id,
        label=label,
        scopes=["portfolio:read"],
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    await token_record.insert()

    print(f"Created portfolio site token for {email}")
    if label:
        print(f"Label: {label}")
    print("\nStore this token as VITE_YARBA_PORTFOLIO_TOKEN (shown once):\n")
    print(raw_token)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a read-only portfolio site token"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Yarba user email (server-side lookup only)",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Optional label, e.g. mujakayadan.com",
    )
    parser.add_argument(
        "--revoke-existing",
        action="store_true",
        help="Revoke any active tokens for this user before creating a new one",
    )
    args = parser.parse_args()
    asyncio.run(create_token(args.email, args.label, args.revoke_existing))


if __name__ == "__main__":
    main()
