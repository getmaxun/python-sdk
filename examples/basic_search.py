"""Search the web. "discover" returns links only; "scrape" also scrapes each result."""
import asyncio
import json

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.search("AI News This Week", "AI model releases", time_range="week", limit=10)  # discover is the default
        result = await robot.run()
        print(json.dumps(result.search_data, indent=2)[:2000])

        # Scrape mode: also opens each result and scrapes it as markdown
        robot = await maxun.search("Python Packaging News", "python packaging news", mode="scrape", limit=5)


asyncio.run(main())
