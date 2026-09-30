"""Detect changes on a page between runs."""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await maxun.scrape.create(
            "World Population Monitor",
            "https://www.worldometers.info/world-population/",
            formats=["text"],
            monitor=True,          # or later: await robot.set_monitoring(True)
        )

        await robot.run()          # first run is the baseline
        result = await robot.run()
        print("Changed:", result.has_changes, result.changed_formats)

        diff = await robot.get_run_diff(result.run_id)
        for format_diff in diff["diffs"]:
            print(f"--- {format_diff['format']}")
            for change in format_diff["changes"][:20]:
                if change["added"] or change["removed"]:
                    print("+" if change["added"] else "-", change["value"][:200])


asyncio.run(main())
