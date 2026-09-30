"""Scrape one page as Markdown, plain text and a screenshot."""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()  # reads MAXUN_API_KEY / MAXUN_BASE_URL from ../.env


async def main():
    async with Maxun() as maxun:
        robot = await maxun.scrape.create(
            "Example Domain Scraper",
            "https://example.com",
            formats=["markdown", "text", "screenshot-visible"],
        )
        result = await robot.run()

        print(result.markdown)
        print(f"{len(result.text or '')} characters of text, {len(result.screenshots)} screenshot(s)")


asyncio.run(main())
