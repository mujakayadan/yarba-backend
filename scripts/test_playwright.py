import asyncio
import sys

from playwright.async_api import async_playwright


async def main_logic(p):
    browser = await p.chromium.launch()
    print("Browser launched successfully!")
    await browser.close()


async def main():
    async with async_playwright() as p:
        await main_logic(p)


if __name__ == "__main__":
    if sys.platform == "win32":
        print("Setting WindowsProactorEventLoopPolicy for asyncio.")
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        # asyncio.run() will use the Proactor event loop due to the policy set above.
        asyncio.run(main())
        print("Playwright test finished.")
    else:
        asyncio.run(main())
