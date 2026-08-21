"""Process due account deletions and expired export archives."""

import asyncio

from core.database.init import init_db
from core.services.account_data_service import AccountDataService


async def main() -> None:
    client = await init_db()
    if client is None:
        raise RuntimeError("Database initialization failed")
    try:
        service = AccountDataService()
        deletions = await service.process_due_deletions()
        exports = await service.purge_expired_exports()
        print(f"Processed {deletions} account deletions and {exports} expired exports")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
