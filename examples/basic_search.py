"""Search the web. "discover" returns links only; "scrape" also scrapes each result."""
import asyncio
import json

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.search("AI model releases", mode="discover", time_range="week", limit=10)
        result = await robot.run()
        print(json.dumps(result.search_data, indent=2)[:2000])

        # Scrape mode (the default): also scrapes each result as markdown
        robot = await maxun.search("python packaging news", limit=5)


asyncio.run(main())
