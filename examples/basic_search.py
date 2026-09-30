"""Search the web. "discover" returns links only; "scrape" also scrapes each result."""
import asyncio
import json

from dotenv import load_dotenv
from maxun import Maxun, SearchConfig

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.search(
            "AI News This Week",
            SearchConfig(query="AI model releases", mode="discover", time_range="week", limit=10),
        )
        result = await robot.run()
        print(json.dumps(result.search_data, indent=2)[:2000])

        # Shorthand: just a query string (scrape mode, markdown of each result)
        robot = await maxun.search("Python packaging news", "python packaging news")


asyncio.run(main())
