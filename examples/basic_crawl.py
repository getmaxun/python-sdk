"""Crawl a site and scrape every page found."""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.crawl(
            "https://www.ycombinator.com/blog",
            mode="path",              # stay under /blog ("domain" | "subdomain" | "path")
            limit=10,                 # at most 10 pages
            max_depth=2,
            exclude_paths=["/tag/*"],
            formats=["markdown"],
        )
        result = await robot.run()

        for page in result.crawl_data:
            meta = page.get("metadata") or {}
            print(meta.get("url") or page.get("url"), "-", meta.get("title"))


asyncio.run(main())
