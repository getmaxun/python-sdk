"""A realistic setup: a list robot that runs daily, watches for changes and
calls a webhook."""
import asyncio

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await (
            maxun.extract("Trending Books Daily")
            .navigate("https://openlibrary.org/trending/daily")
            .capture_list({"selector": "li.searchResultItem", "max_items": 25})
            .monitor_changes()
            .build()
        )

        await robot.add_webhook("https://your-server.example/maxun-hook")
        await robot.schedule(run_every=1, run_every_unit="DAYS", timezone="UTC", at_time_start="08:00")

        result = await robot.run()        # one run now, to check it works
        print(f"{len(result.list_data)} books; next run {robot.get_schedule()['nextRunAt']}")


asyncio.run(main())
