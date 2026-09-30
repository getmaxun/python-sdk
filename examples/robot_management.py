"""List, find, rename, run, inspect, copy and delete robots."""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun, NotFoundError

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.scrape.create("Books Scraper", "https://books.toscrape.com")

        print([r.name for r in await maxun.robots.list()])          # every robot
        print([r.name for r in await maxun.scrape.list()])          # only scrape robots
        same = await maxun.robots.find("Books Scraper")             # by name
        same = await maxun.robots.get(robot.id)                     # by id
        print(same, same.url, same.formats)

        await robot.rename("Books Scraper (renamed)")

        result = await robot.run()
        runs = await robot.get_runs()                                # newest first
        latest = await robot.get_latest_run()
        run = await robot.get_run(result.run_id)
        print(len(runs), latest["runId"], run["status"])

        copy = await robot.duplicate("https://books.toscrape.com/catalogue/page-2.html")
        await copy.delete()
        await robot.delete()

        try:
            await maxun.robots.get(robot.id)
        except NotFoundError:
            print("Deleted")


asyncio.run(main())
