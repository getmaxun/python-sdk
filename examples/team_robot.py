"""Create robots in a team workspace (Maxun Cloud).

Set MAXUN_TEAM_ID in .env, or pass team_id=... to Maxun().
"""
import asyncio
import os

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun(team_id=os.environ.get("MAXUN_TEAM_ID")) as maxun:
        robot = await maxun.scrape("Team Scraper", "https://example.com")
        print([r.name for r in await maxun.robots.list()])
        result = await robot.run()
        print(result.status)


asyncio.run(main())
