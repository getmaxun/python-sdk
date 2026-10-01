"""Several steps on one robot: capture text and a list from the same page,
naming each capture."""
import asyncio
import json

from dotenv import load_dotenv
from maxun import Maxun

load_dotenv()


async def main():
    async with Maxun() as maxun:
        robot = await (
            maxun.extract("Premier League Table", "https://www.bbc.com/sport/football/tables")
            .capture_text({"Title": "h1"}, name="Heading")
            .capture_list("table tbody tr", max_items=20, name="Standings")
            .build()
        )
        result = await robot.run()
        print(result.text_data)
        print(json.dumps(result.list_data[:5], indent=2))


asyncio.run(main())
