"""Detect changes between runs. Works for scrape, crawl and extract robots."""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        # A single page
        page = await maxun.scrape(
            "World Population Monitor",
            "https://www.worldometers.info/world-population/",
            formats=["text"],
            monitor=True,             # or later: await page.set_monitoring(True)
        )
        await page.run()                     # first run is the baseline
        result = await page.run()
        print("Page changed:", result.has_changes, result.changed_formats)

        diff = await page.get_run_diff(result.run_id)
        for format_diff in diff["diffs"]:
            print(f"--- {format_diff['format']}")
            for change in format_diff["changes"][:20]:
                if change["added"] or change["removed"]:
                    print("+" if change["added"] else "-", change["value"][:200])

        # A whole section of a site: also reports which pages appeared, vanished or changed
        site = await maxun.crawl("YC Blog Monitor", "https://www.ycombinator.com/blog", mode="path", limit=10, monitor=True)
        await site.run()
        result = await site.run()
        print("Pages:", result.changed_pages)

        # Captured data from selectors
        listing = await (
            maxun.extract("HN Front Page Monitor", "https://news.ycombinator.com", monitor=True)
            .capture_list("tr.athing", max_items=30)
            .build()
        )
        await listing.run()
        result = await listing.run()
        print("List changed:", result.has_changes, result.changed_formats)


asyncio.run(main())
